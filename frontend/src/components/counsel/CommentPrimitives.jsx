/**
 * Shared comment primitives used across the Diff modal.
 *
 * Exports:
 *   - CommentCard: individual comment with reply / resolve / delete controls
 *   - InlineCommentThread: renders roots + replies + inline reply compose
 *   - ComposeForm: textarea + submit/cancel with live @mention hint
 *   - GeneralCommentsPanel: below-diff panel for un-anchored comments
 *   - renderCommentBody: helper to convert @admin/@counsel to pill spans
 */
import React, { useState } from "react";
import {
  CheckCircle2, CornerDownRight, Trash2, MessageCircle, Send,
} from "lucide-react";

// -------- @mention helpers --------
const MENTION_RX_TEST = /(?<![\w.])@(admin|counsel)\b/i;
const MENTION_RX_GLOBAL = /(?<![\w.])@(admin|counsel)\b/gi;

export function renderCommentBody(body) {
  if (!body) return null;
  const parts = [];
  MENTION_RX_GLOBAL.lastIndex = 0;
  let last = 0;
  let m;
  while ((m = MENTION_RX_GLOBAL.exec(body)) !== null) {
    if (m.index > last) parts.push(body.slice(last, m.index));
    parts.push(
      <span
        key={`m-${m.index}`}
        className="inline-block text-[11px] uppercase tracking-wider bg-[#F5E6D6] text-[#7A4A1A] rounded-full px-2 py-0.5 font-semibold mx-0.5"
      >
        @{m[1].toLowerCase()}
      </span>,
    );
    last = m.index + m[0].length;
  }
  if (last < body.length) parts.push(body.slice(last));
  return parts;
}

// -------- CommentCard --------
export function CommentCard({ comment, replies, currentUser, onReplyClick, onResolve, onDelete }) {
  // Indirect self-reference — direct <CommentCard/> recursion crashes
  // the @emergentbase/visual-edits babel plugin. Alias avoids the cycle.
  const NestedCard = CommentCard;
  const canDelete = currentUser?.role === "admin" || currentUser?.id === comment.author_id;
  return (
    <div
      className={`rounded border p-3 text-xs bg-white ${comment.resolved ? "border-[#CEE0CE] opacity-70" : "border-[#E5E1D8]"}`}
      data-testid={`comment-${comment.id}`}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <strong className="text-[#0F2424] text-[13px]">{comment.author_email}</strong>
        <span className="text-[10px] uppercase tracking-wider rounded-full bg-[#F0EDE3] px-1.5 py-0.5 text-[#5C6B6B]">{comment.author_role}</span>
        <span className="text-[#5C6B6B]">· {new Date(comment.created_at).toLocaleString()}</span>
        {comment.line_number != null && (
          <span className="text-[10px] uppercase tracking-wider text-[#7A4A1A] font-semibold">Line {comment.line_number}</span>
        )}
        {comment.resolved && (
          <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#EAF3EA] text-[#1E4030] rounded-full px-2 py-0.5 font-semibold">
            <CheckCircle2 size={10} /> Resolved
          </span>
        )}
      </div>
      <p className="mt-2 text-[#0F2424] whitespace-pre-wrap leading-relaxed" data-testid={`comment-${comment.id}-body`}>
        {renderCommentBody(comment.body)}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          onClick={onReplyClick}
          className="text-[11px] uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] font-semibold inline-flex items-center gap-1"
          data-testid={`comment-${comment.id}-reply`}
        >
          <CornerDownRight size={12} /> Reply
        </button>
        <button
          onClick={() => onResolve(comment, !comment.resolved)}
          className="text-[11px] uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] font-semibold"
          data-testid={`comment-${comment.id}-resolve`}
        >
          {comment.resolved ? "Reopen" : "Resolve"}
        </button>
        {canDelete && (
          <button
            onClick={() => onDelete(comment)}
            className="text-[11px] uppercase tracking-wider text-[#9E3C3C] hover:text-[#0F2424] font-semibold inline-flex items-center gap-1"
            data-testid={`comment-${comment.id}-delete`}
          >
            <Trash2 size={12} /> Delete
          </button>
        )}
      </div>
      {replies.length > 0 && (
        <div className="mt-3 pl-4 border-l-2 border-[#E5E1D8] space-y-2">
          {replies.map((r) => (
            <NestedCard
              key={r.id}
              comment={r}
              replies={[]}
              currentUser={currentUser}
              onReplyClick={onReplyClick}
              onResolve={onResolve}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// -------- ComposeForm --------
export function ComposeForm({ placeholder, value, onChange, onCancel, onSubmit, busy, testidPrefix }) {
  const hasMentions = MENTION_RX_TEST.test(value || "");
  return (
    <div className="font-sans">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="input input-bordered w-full text-sm min-h-[70px]"
        data-testid={`${testidPrefix}-textarea`}
      />
      <div className="mt-2 flex items-center justify-between gap-2 flex-wrap">
        <p className="text-[10px] text-[#5C6B6B]">
          Tip: type <code className="text-[#7A4A1A]">@admin</code> or <code className="text-[#7A4A1A]">@counsel</code> to notify by email (delivered as a once-daily digest).
          {hasMentions && (
            <span className="ml-2 inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#F5E6D6] text-[#7A4A1A] rounded-full px-2 py-0.5 font-semibold" data-testid={`${testidPrefix}-mention-hint`}>
              Will notify in next digest
            </span>
          )}
        </p>
        <div className="flex gap-2">
          <button onClick={onCancel} className="btn-outline text-xs" data-testid={`${testidPrefix}-cancel`}>Cancel</button>
          <button
            onClick={onSubmit}
            disabled={busy || !value.trim()}
            className="btn-primary text-xs inline-flex items-center gap-1"
            data-testid={`${testidPrefix}-submit`}
          >
            <Send size={12} /> {busy ? "Posting…" : "Post"}
          </button>
        </div>
      </div>
    </div>
  );
}

// -------- InlineCommentThread --------
export function InlineCommentThread({ comments, allComments, lineNumber, currentUser, onReply, onResolve, onDelete }) {
  const [replyTo, setReplyTo] = useState(null);
  const [replyBody, setReplyBody] = useState("");
  const [busy, setBusy] = useState(false);
  const roots = comments.filter((c) => !c.parent_id);
  return (
    <div className="space-y-3 font-sans" data-testid={`inline-thread-line-${lineNumber ?? "general"}`}>
      {roots.map((c) => (
        <CommentCard
          key={c.id}
          comment={c}
          replies={allComments.filter((r) => r.parent_id === c.id)}
          currentUser={currentUser}
          onReplyClick={() => { setReplyTo(c.id); setReplyBody(""); }}
          onResolve={onResolve}
          onDelete={onDelete}
        />
      ))}
      {replyTo && (
        <ComposeForm
          placeholder="Write a reply…"
          value={replyBody}
          onChange={setReplyBody}
          onCancel={() => { setReplyTo(null); setReplyBody(""); }}
          onSubmit={async () => {
            if (!replyBody.trim()) return;
            setBusy(true);
            try {
              await onReply(replyBody.trim(), replyTo);
              setReplyTo(null);
              setReplyBody("");
            } finally { setBusy(false); }
          }}
          busy={busy}
          testidPrefix={`reply-line-${lineNumber ?? "general"}`}
        />
      )}
    </div>
  );
}

// -------- GeneralCommentsPanel --------
export function GeneralCommentsPanel({ comments, allComments, currentUser, composing, composeBody, setComposeBody, onPost, onResolve, onDelete }) {
  const [showCompose, setShowCompose] = useState(false);
  const roots = comments.filter((c) => !c.parent_id);
  return (
    <div className="border-t border-[#E5E1D8] px-5 py-4 bg-[#FAF7F0]" data-testid="diff-general-comments-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs uppercase tracking-wider text-[#476B6B] font-semibold inline-flex items-center gap-1">
          <MessageCircle size={12} /> General comments · {roots.length}
        </h3>
        {!showCompose && (
          <button
            onClick={() => setShowCompose(true)}
            className="text-xs uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] font-semibold"
            data-testid="diff-general-add-btn"
          >
            + New comment
          </button>
        )}
      </div>
      {showCompose && (
        <div className="mb-4">
          <ComposeForm
            placeholder="Leave a general note about this working draft…"
            value={composeBody}
            onChange={setComposeBody}
            onCancel={() => { setShowCompose(false); setComposeBody(""); }}
            onSubmit={async () => {
              if (!composeBody.trim()) return;
              await onPost(composeBody.trim(), null);
              setShowCompose(false);
            }}
            busy={composing}
            testidPrefix="diff-general-compose"
          />
        </div>
      )}
      {roots.length === 0 && !showCompose && (
        <p className="text-xs text-[#5C6B6B]">No general comments yet. Use the <strong>+</strong> button on any line in the diff to ask about a specific spot, or add a general note here.</p>
      )}
      {roots.length > 0 && (
        <InlineCommentThread
          comments={roots}
          allComments={allComments}
          lineNumber={null}
          currentUser={currentUser}
          onReply={(body, parentId) => onPost(body, parentId)}
          onResolve={onResolve}
          onDelete={onDelete}
        />
      )}
    </div>
  );
}
