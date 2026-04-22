use std::env;
use std::sync::Arc;

use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use tokio::sync::mpsc;
use uuid::Uuid;

use rust_inference::application::health_slice::health_status;
use rust_inference::application::inference_slice::command_handler::handle_llm_inference_requested;
use rust_inference::application::inference_slice::service::InferenceService;
use rust_inference::domain::inference::command::LlmInferenceCommand;
use rust_inference::domain::inference::model::InferenceRequest;
use rust_inference::infrastructure::engines::ollama_client::OllamaClient;
use rust_inference::infrastructure::kafka::consumer::KafkaConsumerMock;
use rust_inference::infrastructure::kafka::producer::KafkaPublisherMock;
use rust_inference::infrastructure::telemetry::metrics::MetricsRegistry;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(env::var("RUST_LOG").unwrap_or_else(|_| "info".to_string()))
        .init();

    let model_name = env::var("MODEL_NAME").unwrap_or_else(|_| "phi3:mini".to_string());
    let bind_host = env::var("BIND_HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let bind_port = env::var("PORT")
        .ok()
        .and_then(|port| port.parse::<u16>().ok())
        .unwrap_or(8081);
    let bootstrap_mock_mode = env::var("BOOTSTRAP_MOCK_MODE")
        .map(|v| v.eq_ignore_ascii_case("true"))
        .unwrap_or(true);

    let (tx, mut rx) = mpsc::channel::<LlmInferenceCommand>(16);
    // In local/mock mode we bootstrap one synthetic command to test full internal flow quickly.
    // В локальном/mock-режиме подаем синтетическую команду, чтобы быстро проверить полный внутренний поток.
    if bootstrap_mock_mode {
        KafkaConsumerMock::spawn_mock(tx);
    }

    let service = Arc::new(InferenceService::new(
        Arc::new(OllamaClient),
        Arc::new(KafkaPublisherMock::new()),
        Arc::new(MetricsRegistry::new()),
    ));

    let background_service = Arc::clone(&service);
    tokio::spawn(async move {
        // Represents Kafka consumer loop: each LLMInferenceRequested is handled independently.
        // Это имитация Kafka consumer loop: каждая команда LLMInferenceRequested обрабатывается независимо.
        while let Some(command) = rx.recv().await {
            let _ = handle_llm_inference_requested(&background_service, command).await;
        }
    });

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(Arc::clone(&service)))
            .app_data(web::Data::new(model_name.clone()))
            .route("/health", web::get().to(health))
            .route("/infer", web::post().to(infer))
    })
    .bind((bind_host, bind_port))?
    .run()
    .await
}

async fn health() -> impl Responder {
    HttpResponse::Ok().body(health_status())
}

async fn infer(
    req: web::Json<InferenceRequest>,
    service: web::Data<Arc<InferenceService>>,
    model_name: web::Data<String>,
) -> impl Responder {
    // HTTP endpoint mirrors incoming Kafka command shape for isolated/manual testing.
    // HTTP endpoint повторяет форму Kafka-команды для изолированного и ручного тестирования.
    let command = LlmInferenceCommand {
        request_id: Uuid::new_v4().to_string(),
        conversation_id: "http-debug".to_string(),
        model: model_name.get_ref().clone(),
        prompt: req.prompt.clone(),
    };

    match handle_llm_inference_requested(service.get_ref(), command).await {
        Ok(events) => HttpResponse::Ok().json(events),
        Err(err) => HttpResponse::InternalServerError().body(err),
    }
}
