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
    // Published multiple times per request to support downstream streaming transport.
    // Публикуется многократно в рамках запроса для потоковой доставки в downstream.
    LlmResponseChunkGenerated(LlmResponseChunkGeneratedEvent),
    // Published exactly once per request as terminal "response is complete" signal.
    // Публикуется ровно один раз на запрос как финальный сигнал "ответ завершен".
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
