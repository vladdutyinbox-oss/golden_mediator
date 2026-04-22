use std::sync::{Arc, Mutex};

use async_trait::async_trait;

use crate::application::inference_slice::ports::KafkaPublisherPort;
use crate::domain::inference::event::InferenceEvent;

#[derive(Default)]
pub struct KafkaPublisherMock {
    events: Arc<Mutex<Vec<InferenceEvent>>>,
}

impl KafkaPublisherMock {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn published_events(&self) -> Vec<InferenceEvent> {
        self.events.lock().expect("events mutex poisoned").clone()
    }
}

#[async_trait]
impl KafkaPublisherPort for KafkaPublisherMock {
    async fn publish(&self, event: InferenceEvent) -> Result<(), String> {
        self.events
            .lock()
            .map_err(|_| "events mutex poisoned".to_string())?
            .push(event);
        Ok(())
    }
}
