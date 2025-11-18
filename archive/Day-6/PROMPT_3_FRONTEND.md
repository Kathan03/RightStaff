# 🎨 DAY-6 PROMPT 3: COMPLETE FRONTEND IMPLEMENTATION

**Estimated Time:** 10-12 hours
**Complexity:** Advanced
**Prerequisites:** PROMPT_1 and PROMPT_2 complete, backend APIs working

---

## 🎯 Objective

Build a production-grade React frontend with:
1. **Candidate Portal** - Resume upload, form pre-fill, job application
2. **Recruiter Dashboard** - Job creation, ranked candidates, chatbot, email drafting
3. **Modern Stack** - React 18, TypeScript, Tailwind CSS, Zustand
4. **Real-time Features** - WebSocket chatbot, live ranking updates

---

## 📦 Step 1: Initialize React + TypeScript Project

```bash
cd /home/user/RightStaff

# Create React app with TypeScript
npx create-react-app frontend --template typescript

cd frontend

# Install dependencies
npm install \
  react-router-dom@6 \
  @types/react-router-dom \
  zustand \
  axios \
  react-hook-form \
  zod \
  @hookform/resolvers \
  tailwindcss@3 \
  postcss \
  autoprefixer \
  lucide-react \
  react-dropzone

# Initialize Tailwind
npx tailwindcss init -p
```

---

## 🎨 Step 2: Configure Tailwind CSS

**File:** `frontend/tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
}
```

**File:** `frontend/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-50 text-gray-900;
  }
}

@layer components {
  .btn-primary {
    @apply px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
  }

  .btn-secondary {
    @apply px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors;
  }

  .input-field {
    @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent;
  }

  .card {
    @apply bg-white rounded-lg shadow-md p-6;
  }
}
```

---

## 🗂️ Step 3: Project Structure

Create the following folder structure:

```
frontend/src/
├── api/                 # API client functions
│   ├── client.ts
│   ├── candidates.ts
│   ├── jobs.ts
│   └── chat.ts
├── components/          # Reusable components
│   ├── candidate/
│   │   ├── ResumeUpload.tsx
│   │   ├── CandidateForm.tsx
│   │   └── JobList.tsx
│   ├── recruiter/
│   │   ├── JobForm.tsx
│   │   ├── CandidateRanking.tsx
│   │   ├── Chatbot.tsx
│   │   └── EmailViewer.tsx
│   └── shared/
│       ├── Navbar.tsx
│       ├── Loading.tsx
│       └── ErrorBoundary.tsx
├── pages/              # Page components
│   ├── CandidatePortal.tsx
│   ├── RecruiterDashboard.tsx
│   └── NotFound.tsx
├── store/              # Zustand state management
│   ├── candidateStore.ts
│   └── recruiterStore.ts
├── types/              # TypeScript types
│   └── index.ts
├── utils/              # Utility functions
│   └── validation.ts
├── App.tsx
└── index.tsx
```

---

## 📡 Step 4: API Client Setup

**File:** `frontend/src/api/client.ts`

```typescript
import axios, { AxiosInstance } from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message;
    console.error(`[API Error] ${message}`);
    return Promise.reject(error);
  }
);
```

**File:** `frontend/src/api/candidates.ts`

```typescript
import { apiClient } from './client';

export interface ParsedCandidate {
  full_name: string;
  email: string;
  phone: string | null;
  location: string | null;
  years_experience: number | null;
  professional_summary: string;
  skills: string[];
}

export interface UploadResumeResponse {
  temp_id: string;
  parsed_data: ParsedCandidate;
}

export interface CreateCandidateRequest {
  temp_id: string;
  full_name: string;
  email: string;
  phone?: string;
  location?: string;
  years_experience?: number;
  skills: string[];
  professional_summary: string;
  desired_salary?: number;
  work_authorization?: string;
}

export const candidatesApi = {
  // Upload resume (anonymous)
  uploadResume: async (file: File): Promise<UploadResumeResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await apiClient.post('/api/v1/candidates/upload-resume', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // Create full candidate profile
  createCandidate: async (request: CreateCandidateRequest) => {
    const { data } = await apiClient.post('/api/v1/candidates/create-full', request);
    return data;
  },

  // Get all jobs
  getJobs: async () => {
    const { data } = await apiClient.get('/api/v1/jobs');
    return data;
  },

  // Apply to job
  applyToJob: async (jobId: string, candidateId: string) => {
    const { data } = await apiClient.post(`/api/v1/jobs/${jobId}/apply`, {
      candidate_id: candidateId,
    });
    return data;
  },
};
```

**File:** `frontend/src/api/jobs.ts`

```typescript
import { apiClient } from './client';

export interface CreateJobRequest {
  title: string;
  description: string;
  company_name?: string;
  location?: string;
  salary_min?: number;
  salary_max?: number;
  required_skills: string[];
  experience_years_min?: number;
}

export interface RankedCandidate {
  candidate_id: string;
  full_name: string;
  email: string;
  professional_summary: string;
  skills: string[];
  years_experience: number | null;
  final_score: number;
  dense_score: number;
  structured_score: number;
  pairwise_score: number;
  completeness_score: number;
}

export const jobsApi = {
  // Create job
  createJob: async (request: CreateJobRequest) => {
    const { data } = await apiClient.post('/api/v1/jobs', request);
    return data;
  },

  // Get all jobs
  getAllJobs: async () => {
    const { data } = await apiClient.get('/api/v1/jobs');
    return data;
  },

  // Get job by ID
  getJob: async (jobId: string) => {
    const { data } = await apiClient.get(`/api/v1/jobs/${jobId}`);
    return data;
  },

  // Rank candidates for job
  rankCandidates: async (jobId: string, applicantsOnly = true): Promise<RankedCandidate[]> => {
    const endpoint = applicantsOnly
      ? `/api/v1/jobs/${jobId}/rank`
      : `/api/v1/jobs/${jobId}/rank_full`;
    const { data } = await apiClient.post(endpoint);
    return data;
  },
};
```

**File:** `frontend/src/api/chat.ts`

```typescript
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  type: 'response' | 'error';
  content?: string;
  citations?: string[];
  message?: string;
}

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private jobId: string;

  constructor(jobId: string) {
    this.jobId = jobId;
  }

  connect(
    onMessage: (response: ChatResponse) => void,
    onError: (error: Event) => void
  ) {
    const wsUrl = `ws://localhost:8000/api/v1/chat/${this.jobId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[WebSocket] Connected');
    };

    this.ws.onmessage = (event) => {
      const data: ChatResponse = JSON.parse(event.data);
      onMessage(data);
    };

    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      onError(error);
    };

    this.ws.onclose = () => {
      console.log('[WebSocket] Disconnected');
    };
  }

  sendMessage(question: string, history: ChatMessage[]) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ question, history }));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
```

---

## 🏪 Step 5: Zustand State Management

**File:** `frontend/src/store/candidateStore.ts`

```typescript
import create from 'zustand';
import { ParsedCandidate } from '../api/candidates';

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
```

**File:** `frontend/src/store/recruiterStore.ts`

```typescript
import create from 'zustand';
import { RankedCandidate } from '../api/jobs';

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
```

---

## 🧩 Step 6: Candidate Portal Components

**File:** `frontend/src/components/candidate/ResumeUpload.tsx`

```typescript
import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, CheckCircle } from 'lucide-react';
import { candidatesApi } from '../../api/candidates';
import { useCandidateStore } from '../../store/candidateStore';

export const ResumeUpload: React.FC<{ onSuccess: () => void }> = ({ onSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setTempId, setParsedData } = useCandidateStore();

  const onDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const response = await candidatesApi.uploadResume(file);
      setTempId(response.temp_id);
      setParsedData(response.parsed_data);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="card max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 text-center">Upload Your Resume</h2>

      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-colors
          ${isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary-400'}
        `}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-4">
          {uploading ? (
            <>
              <Upload className="w-12 h-12 text-primary-500 animate-bounce" />
              <p className="text-lg font-medium">Parsing your resume...</p>
            </>
          ) : (
            <>
              <FileText className="w-12 h-12 text-gray-400" />
              <p className="text-lg font-medium">
                {isDragActive
                  ? 'Drop your resume here'
                  : 'Drag & drop your resume, or click to browse'}
              </p>
              <p className="text-sm text-gray-500">Supports PDF, DOC, DOCX, TXT</p>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}
    </div>
  );
};
```

**File:** `frontend/src/components/candidate/CandidateForm.tsx`

```typescript
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { candidatesApi, CreateCandidateRequest } from '../../api/candidates';
import { useCandidateStore } from '../../store/candidateStore';

const schema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  phone: z.string().optional(),
  location: z.string().optional(),
  years_experience: z.number().min(0).max(50).optional(),
  skills: z.array(z.string()).min(1, 'At least one skill required'),
  professional_summary: z.string().min(50, 'Summary must be at least 50 characters'),
  desired_salary: z.number().optional(),
  work_authorization: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export const CandidateForm: React.FC<{ onSuccess: () => void }> = ({ onSuccess }) => {
  const { tempId, parsedData, setCandidateId } = useCandidateStore();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors }, setValue } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: parsedData?.full_name || '',
      email: parsedData?.email || '',
      phone: parsedData?.phone || '',
      location: parsedData?.location || '',
      years_experience: parsedData?.years_experience || undefined,
      skills: parsedData?.skills || [],
      professional_summary: parsedData?.professional_summary || '',
    },
  });

  const onSubmit = async (data: FormData) => {
    if (!tempId) {
      setError('No temp_id found. Please upload resume first.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const request: CreateCandidateRequest = {
        temp_id: tempId,
        ...data,
      };
      const response = await candidatesApi.createCandidate(request);
      setCandidateId(response.candidate_id);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Complete Your Profile</h2>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Full Name */}
        <div>
          <label className="block text-sm font-medium mb-2">Full Name *</label>
          <input
            {...register('full_name')}
            className="input-field"
            placeholder="John Doe"
          />
          {errors.full_name && (
            <p className="text-red-600 text-sm mt-1">{errors.full_name.message}</p>
          )}
        </div>

        {/* Email */}
        <div>
          <label className="block text-sm font-medium mb-2">Email *</label>
          <input
            {...register('email')}
            type="email"
            className="input-field"
            placeholder="john@example.com"
          />
          {errors.email && (
            <p className="text-red-600 text-sm mt-1">{errors.email.message}</p>
          )}
        </div>

        {/* Phone */}
        <div>
          <label className="block text-sm font-medium mb-2">Phone</label>
          <input
            {...register('phone')}
            className="input-field"
            placeholder="+1 (555) 123-4567"
          />
        </div>

        {/* Location */}
        <div>
          <label className="block text-sm font-medium mb-2">Location</label>
          <input
            {...register('location')}
            className="input-field"
            placeholder="San Francisco, CA"
          />
        </div>

        {/* Years Experience */}
        <div>
          <label className="block text-sm font-medium mb-2">Years of Experience</label>
          <input
            {...register('years_experience', { valueAsNumber: true })}
            type="number"
            className="input-field"
            placeholder="5"
          />
        </div>

        {/* Skills */}
        <div>
          <label className="block text-sm font-medium mb-2">Skills (comma-separated) *</label>
          <input
            {...register('skills')}
            className="input-field"
            placeholder="Python, React, PostgreSQL"
            onChange={(e) => {
              const skills = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
              setValue('skills', skills);
            }}
          />
          {errors.skills && (
            <p className="text-red-600 text-sm mt-1">{errors.skills.message}</p>
          )}
        </div>

        {/* Professional Summary */}
        <div>
          <label className="block text-sm font-medium mb-2">Professional Summary *</label>
          <textarea
            {...register('professional_summary')}
            rows={5}
            className="input-field"
            placeholder="Brief summary of your experience and expertise..."
          />
          {errors.professional_summary && (
            <p className="text-red-600 text-sm mt-1">{errors.professional_summary.message}</p>
          )}
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="btn-primary w-full"
        >
          {submitting ? 'Submitting...' : 'Create Profile'}
        </button>
      </form>
    </div>
  );
};
```

**File:** `frontend/src/components/candidate/JobList.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { candidatesApi } from '../../api/candidates';
import { Briefcase, MapPin, DollarSign } from 'lucide-react';

interface Job {
  id: string;
  title: string;
  company_name?: string;
  location?: string;
  salary_min?: number;
  salary_max?: number;
  required_skills: string[];
}

export const JobList: React.FC<{ candidateId: string }> = ({ candidateId }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState<string | null>(null);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const data = await candidatesApi.getJobs();
      setJobs(data);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async (jobId: string) => {
    setApplying(jobId);
    try {
      await candidatesApi.applyToJob(jobId, candidateId);
      alert('Application submitted successfully!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Application failed');
    } finally {
      setApplying(null);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading jobs...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Available Jobs</h2>

      <div className="space-y-4">
        {jobs.map((job) => (
          <div key={job.id} className="card hover:shadow-lg transition-shadow">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h3 className="text-xl font-semibold mb-2">{job.title}</h3>
                {job.company_name && (
                  <p className="text-gray-600 mb-2">{job.company_name}</p>
                )}

                <div className="flex flex-wrap gap-4 text-sm text-gray-500 mb-3">
                  {job.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {job.location}
                    </span>
                  )}
                  {job.salary_min && job.salary_max && (
                    <span className="flex items-center gap-1">
                      <DollarSign className="w-4 h-4" />
                      ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {job.required_skills.map((skill) => (
                    <span
                      key={skill}
                      className="px-2 py-1 bg-primary-100 text-primary-700 rounded text-sm"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <button
                onClick={() => handleApply(job.id)}
                disabled={applying === job.id}
                className="btn-primary ml-4"
              >
                {applying === job.id ? 'Applying...' : 'Apply'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 🎯 Step 7: Recruiter Dashboard Components

**File:** `frontend/src/components/recruiter/JobForm.tsx`

```typescript
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { jobsApi, CreateJobRequest } from '../../api/jobs';

export const JobForm: React.FC<{ onSuccess: (jobId: string) => void }> = ({ onSuccess }) => {
  const [submitting, setSubmitting] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<CreateJobRequest>();

  const onSubmit = async (data: CreateJobRequest) => {
    setSubmitting(true);
    try {
      // Convert comma-separated skills to array
      const skills = typeof data.required_skills === 'string'
        ? (data.required_skills as any).split(',').map((s: string) => s.trim())
        : data.required_skills;

      const response = await jobsApi.createJob({ ...data, required_skills: skills });
      onSuccess(response.job_id);
    } catch (err) {
      console.error('Job creation failed:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-6">Create New Job</h2>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Job Title *</label>
          <input
            {...register('title', { required: 'Title is required' })}
            className="input-field"
            placeholder="Senior Python Developer"
          />
          {errors.title && <p className="text-red-600 text-sm">{errors.title.message}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Company Name</label>
          <input {...register('company_name')} className="input-field" placeholder="Acme Corp" />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Description *</label>
          <textarea
            {...register('description', { required: 'Description is required' })}
            rows={4}
            className="input-field"
            placeholder="We're looking for a senior developer..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Required Skills (comma-separated) *</label>
          <input
            {...register('required_skills', { required: 'Skills are required' })}
            className="input-field"
            placeholder="Python, Django, PostgreSQL"
          />
        </div>

        <button type="submit" disabled={submitting} className="btn-primary w-full">
          {submitting ? 'Creating...' : 'Create Job'}
        </button>
      </form>
    </div>
  );
};
```

**File:** `frontend/src/components/recruiter/CandidateRanking.tsx`

```typescript
import React from 'react';
import { RankedCandidate } from '../../api/jobs';
import { Star, TrendingUp } from 'lucide-react';

interface Props {
  candidates: RankedCandidate[];
  onSelectCandidate: (candidate: RankedCandidate) => void;
}

export const CandidateRanking: React.FC<Props> = ({ candidates, onSelectCandidate }) => {
  return (
    <div className="space-y-4">
      <h3 className="text-xl font-bold">Ranked Candidates</h3>

      {candidates.length === 0 ? (
        <p className="text-gray-500">No candidates found</p>
      ) : (
        candidates.map((candidate, index) => (
          <div
            key={candidate.candidate_id}
            className="card hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => onSelectCandidate(candidate)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl font-bold text-primary-600">#{index + 1}</span>
                  <div>
                    <h4 className="text-lg font-semibold">{candidate.full_name}</h4>
                    <p className="text-sm text-gray-500">{candidate.email}</p>
                  </div>
                </div>

                <p className="text-gray-700 mb-3 line-clamp-2">
                  {candidate.professional_summary}
                </p>

                <div className="flex flex-wrap gap-2 mb-3">
                  {candidate.skills.slice(0, 5).map((skill) => (
                    <span
                      key={skill}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm"
                    >
                      {skill}
                    </span>
                  ))}
                </div>

                {candidate.years_experience && (
                  <p className="text-sm text-gray-600">
                    {candidate.years_experience} years experience
                  </p>
                )}
              </div>

              <div className="ml-4 text-right">
                <div className="flex items-center gap-2 mb-2">
                  <Star className="w-5 h-5 text-yellow-500 fill-current" />
                  <span className="text-2xl font-bold text-primary-600">
                    {(candidate.final_score * 100).toFixed(1)}
                  </span>
                </div>

                <div className="text-xs text-gray-500 space-y-1">
                  <div>Dense: {(candidate.dense_score * 100).toFixed(0)}%</div>
                  <div>Structured: {(candidate.structured_score * 100).toFixed(0)}%</div>
                  <div>Pairwise: {(candidate.pairwise_score * 100).toFixed(0)}%</div>
                  <div>Complete: {(candidate.completeness_score * 100).toFixed(0)}%</div>
                </div>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
```

**File:** `frontend/src/components/recruiter/Chatbot.tsx`

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { ChatWebSocket, ChatMessage, ChatResponse } from '../../api/chat';
import { Send } from 'lucide-react';

interface Props {
  jobId: string;
}

export const Chatbot: React.FC<Props> = ({ jobId }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [connecting, setConnecting] = useState(true);
  const chatRef = useRef<ChatWebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const chat = new ChatWebSocket(jobId);
    chatRef.current = chat;

    chat.connect(
      (response: ChatResponse) => {
        if (response.type === 'response' && response.content) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: response.content! },
          ]);
        } else if (response.type === 'error') {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: `Error: ${response.message}` },
          ]);
        }
        setConnecting(false);
      },
      (error) => {
        console.error('WebSocket error:', error);
        setConnecting(false);
      }
    );

    return () => {
      chat.disconnect();
    };
  }, [jobId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || !chatRef.current) return;

    const userMessage: ChatMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);

    chatRef.current.sendMessage(input, messages);
    setInput('');
  };

  return (
    <div className="card h-[600px] flex flex-col">
      <h3 className="text-xl font-bold mb-4">AI Recruiter Assistant</h3>

      {connecting && (
        <div className="text-center text-gray-500 py-4">Connecting to chatbot...</div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`
                max-w-[80%] px-4 py-2 rounded-lg
                ${msg.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-900'}
              `}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask about candidates..."
          className="input-field flex-1"
          disabled={connecting}
        />
        <button
          onClick={handleSend}
          disabled={connecting || !input.trim()}
          className="btn-primary"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};
```

---

## 🔀 Step 8: Page Components

**File:** `frontend/src/pages/CandidatePortal.tsx`

```typescript
import React, { useState } from 'react';
import { ResumeUpload } from '../components/candidate/ResumeUpload';
import { CandidateForm } from '../components/candidate/CandidateForm';
import { JobList } from '../components/candidate/JobList';
import { useCandidateStore } from '../store/candidateStore';
import { CheckCircle } from 'lucide-react';

export const CandidatePortal: React.FC = () => {
  const [step, setStep] = useState<'upload' | 'form' | 'jobs'>('upload');
  const { candidateId } = useCandidateStore();

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      {/* Progress Steps */}
      <div className="max-w-3xl mx-auto mb-8">
        <div className="flex items-center justify-center gap-4">
          <StepIndicator label="Upload Resume" active={step === 'upload'} completed={step !== 'upload'} />
          <div className="w-16 h-0.5 bg-gray-300" />
          <StepIndicator label="Complete Profile" active={step === 'form'} completed={step === 'jobs'} />
          <div className="w-16 h-0.5 bg-gray-300" />
          <StepIndicator label="Apply to Jobs" active={step === 'jobs'} completed={false} />
        </div>
      </div>

      {/* Content */}
      {step === 'upload' && <ResumeUpload onSuccess={() => setStep('form')} />}
      {step === 'form' && <CandidateForm onSuccess={() => setStep('jobs')} />}
      {step === 'jobs' && candidateId && <JobList candidateId={candidateId} />}
    </div>
  );
};

const StepIndicator: React.FC<{ label: string; active: boolean; completed: boolean }> = ({
  label,
  active,
  completed,
}) => (
  <div className="flex flex-col items-center">
    <div
      className={`
        w-10 h-10 rounded-full flex items-center justify-center mb-2
        ${active ? 'bg-primary-600 text-white' : completed ? 'bg-green-500 text-white' : 'bg-gray-300'}
      `}
    >
      {completed ? <CheckCircle className="w-6 h-6" /> : null}
    </div>
    <span className={`text-sm ${active ? 'font-semibold' : ''}`}>{label}</span>
  </div>
);
```

**File:** `frontend/src/pages/RecruiterDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { JobForm } from '../components/recruiter/JobForm';
import { CandidateRanking } from '../components/recruiter/CandidateRanking';
import { Chatbot } from '../components/recruiter/Chatbot';
import { jobsApi, RankedCandidate } from '../api/jobs';
import { useRecruiterStore } from '../store/recruiterStore';

export const RecruiterDashboard: React.FC = () => {
  const [view, setView] = useState<'create' | 'rank'>('create');
  const { selectedJobId, rankedCandidates, setSelectedJobId, setRankedCandidates, setLoading } =
    useRecruiterStore();

  const handleJobCreated = async (jobId: string) => {
    setSelectedJobId(jobId);
    setView('rank');
    await loadRankings(jobId);
  };

  const loadRankings = async (jobId: string) => {
    setLoading(true);
    try {
      const candidates = await jobsApi.rankCandidates(jobId, true);
      setRankedCandidates(candidates);
    } catch (err) {
      console.error('Failed to load rankings:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm mb-8">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">Recruiter Dashboard</h1>
          <div className="flex gap-4 mt-4">
            <button
              onClick={() => setView('create')}
              className={view === 'create' ? 'btn-primary' : 'btn-secondary'}
            >
              Create Job
            </button>
            <button
              onClick={() => setView('rank')}
              className={view === 'rank' ? 'btn-primary' : 'btn-secondary'}
              disabled={!selectedJobId}
            >
              View Rankings
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4">
        {view === 'create' && <JobForm onSuccess={handleJobCreated} />}

        {view === 'rank' && selectedJobId && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <CandidateRanking
              candidates={rankedCandidates}
              onSelectCandidate={(c) => console.log('Selected:', c)}
            />
            <Chatbot jobId={selectedJobId} />
          </div>
        )}
      </div>
    </div>
  );
};
```

---

## 🚦 Step 9: App Routing

**File:** `frontend/src/App.tsx`

```typescript
import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { CandidatePortal } from './pages/CandidatePortal';
import { RecruiterDashboard } from './pages/RecruiterDashboard';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <nav className="bg-primary-600 text-white p-4">
          <div className="max-w-7xl mx-auto flex gap-6">
            <Link to="/" className="hover:underline">Candidate Portal</Link>
            <Link to="/recruiter" className="hover:underline">Recruiter Dashboard</Link>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<CandidatePortal />} />
          <Route path="/recruiter" element={<RecruiterDashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
```

---

## ✅ Validation & Testing

### Test 1: Development Server

```bash
cd frontend
npm start

# Visit: http://localhost:3000
```

### Test 2: Candidate Flow

1. Navigate to http://localhost:3000
2. Upload a test resume (PDF/DOC/TXT)
3. Verify form pre-fills with parsed data
4. Edit and submit form
5. Apply to a job

### Test 3: Recruiter Flow

1. Navigate to http://localhost:3000/recruiter
2. Create a new job posting
3. View ranked candidates
4. Test chatbot with questions like:
   - "Who has 5+ years Python?"
   - "Show me candidates with React skills"

### Test 4: Production Build

```bash
npm run build
# Check build/ directory
```

---

## 🐛 Troubleshooting

**Issue 1: CORS Errors**

Add to backend `main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issue 2: WebSocket Connection Failed**

Check backend WebSocket route is registered and port 8000 is accessible.

**Issue 3: Form Not Pre-filling**

Verify `parsedData` in Zustand store after resume upload.

---

## 📊 Success Criteria

- [ ] Candidate can upload resume and see parsed data
- [ ] Form pre-fills correctly from parsed data
- [ ] Candidate can apply to jobs
- [ ] Recruiter can create jobs
- [ ] Rankings display correctly with scores
- [ ] Chatbot connects via WebSocket
- [ ] Chatbot responds to questions
- [ ] UI is responsive on mobile/desktop

---

**PROMPT 3 Complete! 🎨**

Next: **PROMPT 4** - Database migrations + comprehensive testing
