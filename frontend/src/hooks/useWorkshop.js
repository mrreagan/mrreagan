/**
 * Hook to load a workshop, its reviews, public impact statements, and
 * the current user's registration status. Centralizes data fetching so
 * the page component stays a thin composition layer.
 */
import { useEffect, useState } from "react";
import api from "../lib/api";

export default function useWorkshop(slug, user) {
  const [workshop, setWorkshop] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [publicImpacts, setPublicImpacts] = useState([]);
  const [registered, setRegistered] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const userId = user?.id || null;

    const loadWorkshop = async () => {
      try {
        const { data } = await api.get(`/workshops/${slug}`);
        if (cancelled) return;
        setWorkshop(data);
        await Promise.all([
          loadReviews(data.id),
          loadImpacts(data.id),
          userId ? loadRegistration(data.id) : null,
        ]);
      } catch (err) {
        console.error(`Failed to load workshop ${slug}:`, err);
      }
    };

    const loadReviews = async (id) => {
      try {
        const { data } = await api.get(`/reviews?workshop_id=${id}`);
        if (!cancelled) setReviews(data);
      } catch (err) {
        console.warn(`Failed to load reviews for workshop ${id}:`, err);
      }
    };

    const loadImpacts = async (id) => {
      try {
        const { data } = await api.get(`/impact-statements?workshop_id=${id}&public_only=true`);
        if (!cancelled) setPublicImpacts(data);
      } catch (err) {
        console.warn(`Failed to load impact statements for workshop ${id}:`, err);
      }
    };

    const loadRegistration = async (id) => {
      try {
        const { data } = await api.get(`/workshops/${id}/my-registration`);
        if (!cancelled) setRegistered(Boolean(data.registered));
      } catch (err) {
        console.warn(`Failed to load registration for workshop ${id}:`, err);
      }
    };

    loadWorkshop();
    return () => {
      cancelled = true;
    };
  }, [slug, user?.id]);

  return { workshop, reviews, publicImpacts, registered };
}
