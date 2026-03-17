import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "../lib/apiClient";

export function useProfile(userId: string) {
  const queryClient = useQueryClient();

  const profile = useQuery({
    queryKey: ["profile", userId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/profile/${userId}`);
      return data;
    },
    enabled: Boolean(userId)
  });

  const saveProfile = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await apiClient.put(`/api/profile/${userId}`, payload);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile", userId] })
  });

  return { profile, saveProfile };
}
