import React, { useCallback, useEffect, useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";

function DiscussionItem({ item }) {
  return (
    <div className="card p-5" data-testid={`disc-${item.id}`}>
      <div className="flex items-center justify-between text-xs text-[#5C6B6B]">
        <span><strong className="text-[#1A2424]">{item.user_name}</strong> · {item.user_role}</span>
        <div className="flex gap-2">
          {item.is_private && <span className="bg-[#C9A961]/15 text-[#C9A961] px-2 py-0.5 rounded-full">Private</span>}
          {item.answered && <span className="bg-[#2E5C46]/10 text-[#2E5C46] px-2 py-0.5 rounded-full">Answered</span>}
        </div>
      </div>
      <p className="text-sm text-[#1A2424] mt-3 leading-relaxed whitespace-pre-line">{item.content}</p>
      <p className="text-xs text-[#5C6B6B] mt-3">{new Date(item.created_at).toLocaleString()}</p>
    </div>
  );
}

function DiscussionList({ items, isQuestion }) {
  if (items.length === 0) {
    return (
      <div className="card p-8 text-center text-sm text-[#5C6B6B]">
        {isQuestion ? "No questions yet. Be the first to ask." : "No posts yet. Be the first."}
      </div>
    );
  }
  return items.map((it) => <DiscussionItem key={it.id} item={it} />);
}

function NewDiscussionForm({ type, isQuestion, content, setContent, isPrivate, setIsPrivate, onSubmit }) {
  return (
    <div className="card p-5 h-fit sticky top-24">
      <span className="label">{isQuestion ? "Ask a question" : "Start a thread"}</span>
      <form onSubmit={onSubmit} className="mt-3 space-y-3">
        <textarea
          rows={5}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={isQuestion ? "What would you like to ask?" : "Share with the cohort"}
          className="input-field resize-none"
          data-testid={`${type}-textarea`}
        />
        {isQuestion && (
          <label className="flex items-center gap-2 text-xs text-[#5C6B6B]">
            <input
              type="checkbox"
              checked={isPrivate}
              onChange={(e) => setIsPrivate(e.target.checked)}
              className="accent-[#476B6B]"
              data-testid={`${type}-private`}
            />
            Send privately to facilitator
          </label>
        )}
        <button type="submit" disabled={!content.trim()} className="btn-primary w-full justify-center text-sm" data-testid={`${type}-submit`}>
          <Send size={14} strokeWidth={1.5} /> Post
        </button>
      </form>
    </div>
  );
}

export default function DiscussionTab({ workshop, type }) {
  const [items, setItems] = useState([]);
  const [content, setContent] = useState("");
  const [isPrivate, setIsPrivate] = useState(false);
  const isQuestion = type === "qa";

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/discussions?workshop_id=${workshop.id}&is_question=${isQuestion}`);
      setItems(data);
    } catch (err) {
      console.error("Failed to load discussions:", err?.message || err);
    }
  }, [workshop.id, isQuestion]);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!content.trim()) return;
    try {
      await api.post("/discussions", {
        workshop_id: workshop.id,
        content,
        is_question: isQuestion,
        is_private: isPrivate,
      });
      setContent("");
      setIsPrivate(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not post");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid={`tab-${type}`}>
      <div className="lg:col-span-2 space-y-3">
        <DiscussionList items={items} isQuestion={isQuestion} />
      </div>
      <NewDiscussionForm
        type={type}
        isQuestion={isQuestion}
        content={content}
        setContent={setContent}
        isPrivate={isPrivate}
        setIsPrivate={setIsPrivate}
        onSubmit={submit}
      />
    </div>
  );
}
