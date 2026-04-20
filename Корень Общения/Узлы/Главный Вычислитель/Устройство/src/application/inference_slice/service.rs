use std::sync::Arc;
use std::time::Instant;

use crate::application::inference_slice::ports::{KafkaPublisherPort, LlmEnginePort};
use crate::domain::inference::command::LlmInferenceCommand;
use crate::domain::inference::event::{
    InferenceEvent, LlmResponseChunkGeneratedEvent, LlmResponseGeneratedEvent,
};
use crate::infrastructure::telemetry::metrics::MetricsRegistry;

pub struct InferenceService {
    engine: Arc<dyn LlmEnginePort>,
    publisher: Arc<dyn KafkaPublisherPort>,
    metrics: Arc<MetricsRegistry>,
}

impl InferenceService {
    pub fn new(
        engine: Arc<dyn LlmEnginePort>,
        publisher: Arc<dyn KafkaPublisherPort>,
        metrics: Arc<MetricsRegistry>,
    ) -> Self {
        Self {
            engine,
            publisher,
            metrics,
        }
    }

    pub async fn handle_command(
        &self,
        cmd: LlmInferenceCommand,
    ) -> Result<Vec<InferenceEvent>, String> {
        let start = Instant::now();
        let mut full_response = String::new();
        let mut tokens = 0_u64;
        let mut events = Vec::new();
        let mut stream = self.engine.generate_stream(&cmd.model, &cmd.prompt).await?;

        while let Some(chunk) = stream.recv().await {
            tokens += chunk.split_whitespace().count() as u64;
            full_response.push_str(&chunk);

            let chunk_event = InferenceEvent::LlmResponseChunkGenerated(LlmResponseChunkGeneratedEvent {
                request_id: cmd.request_id.clone(),
                chunk,
                done: false,
            });
            self.publisher.publish(chunk_event.clone()).await?;
            self.metrics.inc_chunks_published();
            events.push(chunk_event);
        }

        let final_event = InferenceEvent::LlmResponseGenerated(LlmResponseGeneratedEvent {
            request_id: cmd.request_id.clone(),
            response: full_response,
        });
        self.publisher.publish(final_event.clone()).await?;
        events.push(final_event);

        self.metrics
            .record_inference_elapsed(start.elapsed(), tokens, 4.0_f64);
        Ok(events)
    }

    pub fn metrics(&self) -> Arc<MetricsRegistry> {
        Arc::clone(&self.metrics)
    }
}
