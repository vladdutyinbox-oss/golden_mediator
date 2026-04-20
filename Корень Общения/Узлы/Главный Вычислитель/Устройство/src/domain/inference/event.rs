use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LlmResponseChunkGeneratedEvent {
    pub request_id: String,
    pub chunk: String,
    pub done: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LlmResponseGeneratedEvent {
    pub request_id: String,
    pub response: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum InferenceEvent {
    LlmResponseChunkGenerated(LlmResponseChunkGeneratedEvent),
    LlmResponseGenerated(LlmResponseGeneratedEvent),
}

pub const INFERENCE_EVENT_SCHEMA: &str = r#"{
  "type":"record",
  "name":"InferenceEvent",
  "fields":[
    {"name":"request_id","type":"string"},
    {"name":"event_type","type":"string"},
    {"name":"payload","type":"string"}
  ]
}"#;
