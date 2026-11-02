"""La boucle de l'agent, avec un faux modèle qui joue un scénario écrit à l'avance."""
from analyst.agent import REFUSAL, Agent


class FakeLLM:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, messages, tools=None):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        return self.replies.pop(0)


def say(text):
    return {"content": text, "tool_calls": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}


def tool(code):
    return {"content": "", "tool_calls": [{"id": "c1", "name": "run_pandas", "arguments": {"code": code}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}}


def test_tool_then_answer(clean_df):
    llm = FakeLLM([tool("result = len(df)"), say("Il y a 4 trajets.")])
    res = Agent(llm, clean_df).ask("Combien de trajets ?")
    assert res["status"] == "answered" and res["answer"] == "Il y a 4 trajets."
    t = next(x for x in res["trace"] if x["type"] == "tool")
    assert t["result"] == "4"
    assert llm.calls[1]["messages"][-1] == {"role": "tool", "content": "4", "name": "run_pandas",
                                           "tool_call_id": "c1"}
    assert res["usage"] == {"prompt_tokens": 20, "completion_tokens": 10}


def test_guard_rejects_then_model_fixes(clean_df):
    llm = FakeLLM([tool("result = len(df)"), say("Il y a 5 trajets."), say("Il y a 4 trajets.")])
    res = Agent(llm, clean_df).ask("Combien de trajets ?")
    assert res["status"] == "answered" and "4" in res["answer"]
    assert "ARBITRE" in llm.calls[2]["messages"][-1]["content"]


def test_guard_refuses_after_retries(clean_df):
    llm = FakeLLM([say("Il y a 99 trajets.")] * 3)
    res = Agent(llm, clean_df).ask("Combien de trajets ?")
    assert res["status"] == "refused" and res["answer"] == REFUSAL


def test_blocked_code_is_reported_to_model(clean_df):
    llm = FakeLLM([tool("import os"), say("Je ne peux pas.")])
    res = Agent(llm, clean_df).ask("Liste les fichiers")
    t = next(x for x in res["trace"] if x["type"] == "tool")
    assert t["blocked"] and "BLOQUÉ" in t["result"]


def test_failed_tool_output_is_not_evidence(clean_df):
    # un chiffre présent seulement dans un message d'erreur ne justifie rien
    llm = FakeLLM([tool("result = df['x123']"), say("La réponse est 123."), say("123"), say("123")])
    assert Agent(llm, clean_df).ask("?")["status"] == "refused"


def test_model_alone_has_no_tools(clean_df):
    llm = FakeLLM([say("Environ 100 000 trajets.")])
    res = Agent(llm, clean_df, use_tools=False).ask("Combien de trajets ?")
    assert llm.calls[0]["tools"] is None
    assert res["status"] == "answered" and res["mode"] == "model_alone"


def test_think_tags_removed(clean_df):
    llm = FakeLLM([say("<think>hmm 42</think>Aucun chiffre ici.")])
    assert Agent(llm, clean_df).ask("?")["answer"] == "Aucun chiffre ici."
