"""Le client Ollama, testé sans serveur : on remplace requests.post."""
from analyst import llm


class Resp:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_ollama_request_and_parsing(monkeypatch):
    sent = {}

    def fake_post(url, json, timeout):
        sent.update(url=url, body=json)
        return Resp({"message": {"content": "", "tool_calls": [
            {"function": {"name": "run_pandas", "arguments": {"code": "result = 1"}}}]},
            "prompt_eval_count": 120, "eval_count": 15})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    c = llm.OllamaLLM(model="qwen3.5:4b-q4_K_M", url="http://localhost:11434", num_ctx=16384)
    msgs = [{"role": "user", "content": "q"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c0", "name": "run_pandas", "arguments": {"code": "x"}}]},
            {"role": "tool", "content": "1", "name": "run_pandas", "tool_call_id": "c0"}]
    out = c.chat(msgs, tools=[{"type": "function"}])
    assert sent["url"] == "http://localhost:11434/api/chat"
    assert sent["body"]["options"]["num_ctx"] == 16384  # contexte fixé (section 2 du sujet)
    assert sent["body"]["messages"][1]["tool_calls"][0]["function"]["name"] == "run_pandas"
    assert sent["body"]["messages"][2]["tool_name"] == "run_pandas"
    assert out["tool_calls"] == [{"id": "call_0", "name": "run_pandas", "arguments": {"code": "result = 1"}}]
    assert out["usage"] == {"prompt_tokens": 120, "completion_tokens": 15}


def test_openai_args_string_parsed(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "pas-une-vraie-cle")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Resp({"choices": [{"message": {
        "content": None, "tool_calls": [{"id": "x", "function": {"name": "run_pandas",
                                                                 "arguments": "{\"code\": \"result=2\"}"}}]}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 4}}))
    c = llm.OpenAICompatLLM(model="qwen-3.8-27b", api_key_env="TEST_KEY")
    out = c.chat([{"role": "user", "content": "q"}])
    assert out["content"] == "" and out["tool_calls"][0]["arguments"] == {"code": "result=2"}
