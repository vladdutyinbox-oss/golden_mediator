use async_trait::async_trait;
use tokio::sync::mpsc;

use crate::domain::inference::event::InferenceEvent;

#[async_trait]
pub trait LlmEnginePort: Send + Sync {
    async fn generate_stream(
        &self,
        model: &str,
        prompt: &str,
    ) -> Result<mpsc::Receiver<String>, String>;
}

#[async_trait]
pub trait KafkaPublisherPort: Send + Sync {
    async fn publish(&self, event: InferenceEvent) -> Result<(), String>;
}
