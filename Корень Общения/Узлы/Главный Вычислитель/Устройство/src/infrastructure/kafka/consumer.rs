use tokio::sync::mpsc;

use crate::domain::inference::command::LlmInferenceCommand;

pub struct KafkaConsumerMock;

impl KafkaConsumerMock {
    pub fn spawn_mock(tx: mpsc::Sender<LlmInferenceCommand>) {
        tokio::spawn(async move {
            let command = LlmInferenceCommand {
                request_id: "bootstrap-request".to_string(),
                conversation_id: "bootstrap-conversation".to_string(),
                model: "phi3:mini".to_string(),
                prompt: "Service warmup".to_string(),
            };
            let _ = tx.send(command).await;
        });
    }
}
