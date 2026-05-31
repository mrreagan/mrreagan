import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { MessageSquare, Calendar, Library, Users, Pin, EyeOff, Plus, Trash2, MapPin } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

export default function GatherCommunity() {
  const params = useParams();
  const slug = params["*"] || params.slug;
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("board");
  const [composeBody, setComposeBody] = useState("");
  const [posting, setPosting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/gather/community/${slug}`);
      setData(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't load community");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [slug]);

  const join = async () => {
    if (!user) return toast.error("Sign in to join");
    try { await api.post(`/gather/community/${slug}/join`); toast.success("Welcome 🌿"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Join failed"); }
  };
  const leave = async () => {
    try { await api.post(`/gather/community/${slug}/leave`); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Leave failed"); }
  };
  const post = async (e) => {
    e.preventDefault();
    if (composeBody.trim().length < 2) return;
    setPosting(true);
    try {
      await api.post(`/gather/community/${slug}/posts`, { body: composeBody.trim() });
      setComposeBody("");
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Post failed"); }
    finally { setPosting(false); }
  };
  const pin = async (postId, val) => {
    try { await api.post(`/gather/community/${slug}/posts/${postId}/pin?pinned=${val}`); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Pin failed"); }
  };
  const hide = async (postId) => {
    if (!window.confirm("Hide this post?")) return;
    try { await api.post(`/gather/community/${slug}/posts/${postId}/hide`); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Hide failed"); }
  };

  if (loading || !data) return <div className="container-page py-12">Loading…</div>;
  const c = data.community;
  const canModerate = data.viewer_is_steward || data.viewer_is_admin;

  return (
    <div className="container-page py-12" data-testid="gather-community-page">
      <Link to={`/gather${c.parent_slug ? `?under=${encodeURIComponent(c.parent_slug)}` : ""}`} className="text-xs text-[#476B6B] hover:underline" data-testid="gather-community-back">
        ← back to {c.parent_slug || "all continents"}
      </Link>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <MapPin size={22} strokeWidth={1.2} /> {c.label}
      </h1>
      <div className="divider-flame" />
      <div className="flex items-center gap-3 flex-wrap text-xs text-[#5C6B6B]">
        <span className="uppercase tracking-wider">{c.kind}</span>
        <span>·</span>
        <span className="inline-flex items-center gap-1"><Users size={12} strokeWidth={1.8} /> {c.member_count} members</span>
        <span>·</span>
        <span>{c.post_count} posts</span>
        <span>·</span>
        <span>{c.event_count} events</span>
      </div>

      {/* Join / leave */}
      {user && (
        <div className="mt-4">
          {data.is_member ? (
            <button onClick={leave} className="btn-outline text-xs" data-testid="gather-leave-btn">Leave this community</button>
          ) : (
            <button onClick={join} className="btn-primary text-sm" data-testid="gather-join-btn">Join this community</button>
          )}
        </div>
      )}

      {/* Welcome */}
      {c.welcome_text && (
        <div className="card p-4 mt-6 bg-[#FAF8F5] max-w-2xl" data-testid="gather-welcome">
          <p className="text-xs uppercase tracking-wider text-[#476B6B]">Welcome from your stewards</p>
          <p className="text-sm mt-2 whitespace-pre-wrap leading-relaxed">{c.welcome_text}</p>
        </div>
      )}

      {/* Stewards */}
      {data.stewards.length > 0 && (
        <div className="mt-4 text-xs text-[#5C6B6B]" data-testid="gather-stewards">
          Stewards: {data.stewards.map((s) => s.name).join(" · ")}
        </div>
      )}

      {/* Tabs */}
      <div className="mt-6 border-b border-[#E5E1D8] flex gap-4 text-sm" data-testid="gather-community-tabs">
        {[
          { k: "board", label: "Message board", icon: MessageSquare },
          { k: "events", label: "Events", icon: Calendar },
          { k: "resources", label: "Resources", icon: Library },
        ].map(({ k, label, icon: Icon }) => (
          <button key={k} onClick={() => setTab(k)} className={`pb-2 inline-flex items-center gap-1.5 ${tab === k ? "border-b-2 border-[#9E3C3C] text-[#0F2424]" : "text-[#5C6B6B]"}`} data-testid={`gather-tab-${k}`}>
            <Icon size={14} strokeWidth={1.6} /> {label}
          </button>
        ))}
      </div>

      {tab === "board" && (
        <div className="mt-4 max-w-2xl space-y-3" data-testid="gather-board">
          {user && data.is_member && (
            <form onSubmit={post} className="card p-3" data-testid="gather-compose-form">
              <textarea value={composeBody} onChange={(e) => setComposeBody(e.target.value)} placeholder="Share something with the community…" className="input-field w-full text-sm" rows={3} data-testid="gather-compose-input" />
              <button disabled={posting || composeBody.trim().length < 2} className="btn-primary text-sm mt-2" data-testid="gather-compose-submit">{posting ? "Posting…" : "Post"}</button>
            </form>
          )}
          {data.posts.length === 0 ? (
            <p className="text-sm text-[#5C6B6B] italic">No posts yet. Be the first to say hello.</p>
          ) : data.posts.map((p) => (
            <div key={p.id} className={`card p-3 ${p.pinned ? "border-[#9E3C3C]" : ""}`} data-testid={`gather-post-${p.id}`}>
              <div className="flex items-center justify-between text-xs text-[#5C6B6B]">
                <span><span className="font-medium text-[#0F2424]">{p.author_name}</span> · {p.created_at?.slice(0, 10)}</span>
                {p.pinned && <span className="inline-flex items-center gap-1 text-[#9E3C3C]"><Pin size={10} /> pinned</span>}
              </div>
              <p className="text-sm mt-2 whitespace-pre-wrap leading-relaxed">{p.body}</p>
              {canModerate && (
                <div className="flex gap-2 mt-3 text-xs">
                  <button onClick={() => pin(p.id, !p.pinned)} className="text-[#476B6B] hover:underline" data-testid={`gather-pin-${p.id}`}>
                    <Pin size={11} strokeWidth={1.8} className="inline mr-1" />{p.pinned ? "Unpin" : "Pin"}
                  </button>
                  <button onClick={() => hide(p.id)} className="text-[#9E3C3C] hover:underline" data-testid={`gather-hide-${p.id}`}>
                    <EyeOff size={11} strokeWidth={1.8} className="inline mr-1" />Hide
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "events" && (
        <div className="mt-4 max-w-2xl space-y-2" data-testid="gather-events">
          {data.events.length === 0 ? (
            <p className="text-sm text-[#5C6B6B] italic">No events scheduled yet.{canModerate && " Stewards can add one."}</p>
          ) : data.events.map((e) => (
            <div key={e.id} className="card p-3" data-testid={`gather-event-${e.id}`}>
              <p className="font-serif text-lg">{e.title}</p>
              <p className="text-xs text-[#5C6B6B] mt-1">{e.start_at?.slice(0, 16)?.replace("T", " · ")} · {e.is_virtual ? "Virtual" : e.location_name || "TBD"}</p>
              {e.description && <p className="text-sm mt-2 text-[#5C6B6B]">{e.description}</p>}
            </div>
          ))}
        </div>
      )}

      {tab === "resources" && (
        <div className="mt-4 max-w-2xl space-y-2" data-testid="gather-resources">
          {data.resources.length === 0 ? (
            <p className="text-sm text-[#5C6B6B] italic">No resources yet.</p>
          ) : data.resources.map((r) => (
            <div key={r.id} className={`card p-3 ${r.pinned ? "border-[#C9A961]" : ""}`} data-testid={`gather-resource-${r.id}`}>
              <p className="font-medium text-sm">{r.title}</p>
              {r.url && <a href={r.url} target="_blank" rel="noreferrer noopener" className="text-xs text-[#476B6B] hover:underline">{r.url}</a>}
              {r.body && <p className="text-xs text-[#5C6B6B] mt-1 whitespace-pre-wrap">{r.body}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
