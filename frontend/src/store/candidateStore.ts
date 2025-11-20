import { create } from 'zustand';
import { ParsedCandidate } from '../types';

interface CandidateStore {
  tempId: string | null;
  parsedData: ParsedCandidate | null;
  candidateId: string | null;
  setTempId: (id: string) => void;
  setParsedData: (data: ParsedCandidate) => void;
  setCandidateId: (id: string) => void;
  reset: () => void;
}

export const useCandidateStore = create<CandidateStore>((set) => ({
  tempId: null,
  parsedData: null,
  candidateId: null,
  setTempId: (id) => set({ tempId: id }),
  setParsedData: (data) => set({ parsedData: data }),
  setCandidateId: (id) => set({ candidateId: id }),
  reset: () => set({ tempId: null, parsedData: null, candidateId: null }),
}));
