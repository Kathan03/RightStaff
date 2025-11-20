import { create } from 'zustand';
import { RankedCandidate } from '../types';

interface RecruiterStore {
  selectedJobId: string | null;
  rankedCandidates: RankedCandidate[];
  isLoading: boolean;
  setSelectedJobId: (id: string | null) => void;
  setRankedCandidates: (candidates: RankedCandidate[]) => void;
  setLoading: (loading: boolean) => void;
}

export const useRecruiterStore = create<RecruiterStore>((set) => ({
  selectedJobId: null,
  rankedCandidates: [],
  isLoading: false,
  setSelectedJobId: (id) => set({ selectedJobId: id }),
  setRankedCandidates: (candidates) => set({ rankedCandidates: candidates }),
  setLoading: (loading) => set({ isLoading: loading }),
}));
