use std::sync::Arc;
use std::time::Instant;

use async_trait::async_trait;
use tokio::sync::mpsc;

use rust_inference::application::inference_slice::ports::LlmEnginePort;
use rust_inference::application::inference_slice::service::InferenceService;
use rust_inference::domain::inference::command::LlmInferenceCommand;
use rust_inference::infrastructure::kafka::producer::KafkaPublisherMock;
use rust_inference::infrastructure::telemetry::metrics::MetricsRegistry;

struct FastMockEngine;

#[async_trait]
impl LlmEnginePort for FastMockEngine {
    async fn generate_stream(
        &self,
        _model: &str,
        _prompt: &str,
    ) -> Result<mpsc::Receiver<String>, String> {
        let (tx, rx) = mpsc::channel(16);
        tokio::spawn(async move {
            let chunks = [
                "Привет",
                ", ",
                "это ",
                "потоковый ",
                "ответ ",
                "с ",
                "моками.",
            ];
            for chunk in chunks {
                let _ = tx.send(chunk.to_string()).await;
            }
        });
        Ok(rx)
    }
}

#[tokio::test]
async fn test_full_inference_flow_with_mocks() {
    let publisher = Arc::new(KafkaPublisherMock::new());
    let metrics = Arc::new(MetricsRegistry::new());
    let service = InferenceService::new(Arc::new(FastMockEngine), publisher.clone(), metrics.clone());

    let command = LlmInferenceCommand {
        request_id: "request-1".to_string(),
        conversation_id: "conv-1".to_string(),
        model: "phi3:mini".to_string(),
        prompt: "Скажи привет".to_string(),
    };

    let start = Instant::now();
    let events = service.handle_command(command).await.expect("inference should succeed");
    let elapsed = start.elapsed();

    assert!(!events.is_empty());
    assert!(elapsed.as_millis() < 320, "p95 latency violation");
    assert!(metrics.tokens_per_second() > 60.0);
    assert!(metrics.vram_usage_gb() < 8.0);
    assert_eq!(metrics.chunks_published(), 7);
    assert_eq!(publisher.published_events().len(), 8);
}
