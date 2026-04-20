use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LlmInferenceCommand {
    pub request_id: String,
    pub conversation_id: String,
    pub model: String,
    pub prompt: String,
}
