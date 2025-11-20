import React, { useState } from 'react';
import { ResumeUpload } from '../components/candidate/ResumeUpload';
import { CandidateForm } from '../components/candidate/CandidateForm';
import { JobList } from '../components/candidate/JobList';
import { useCandidateStore } from '../store/candidateStore';
import { CheckCircle, Upload, FileEdit, Briefcase } from 'lucide-react';

type Step = 'upload' | 'form' | 'jobs';

export const CandidatePortal: React.FC = () => {
  const [step, setStep] = useState<Step>('upload');
  const { candidateId } = useCandidateStore();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-12 px-4">
      {/* Progress Steps */}
      <div className="max-w-3xl mx-auto mb-8">
        <div className="flex items-center justify-center gap-2 md:gap-4">
          <StepIndicator
            icon={<Upload className="w-5 h-5" />}
            label="Upload Resume"
            active={step === 'upload'}
            completed={step !== 'upload'}
            stepNumber={1}
          />
          <div className="w-12 md:w-24 h-0.5 bg-gray-300">
            <div
              className={`h-full bg-primary-600 transition-all duration-500 ${
                step !== 'upload' ? 'w-full' : 'w-0'
              }`}
            />
          </div>
          <StepIndicator
            icon={<FileEdit className="w-5 h-5" />}
            label="Complete Profile"
            active={step === 'form'}
            completed={step === 'jobs'}
            stepNumber={2}
          />
          <div className="w-12 md:w-24 h-0.5 bg-gray-300">
            <div
              className={`h-full bg-primary-600 transition-all duration-500 ${
                step === 'jobs' ? 'w-full' : 'w-0'
              }`}
            />
          </div>
          <StepIndicator
            icon={<Briefcase className="w-5 h-5" />}
            label="Apply to Jobs"
            active={step === 'jobs'}
            completed={false}
            stepNumber={3}
          />
        </div>
      </div>

      {/* Content */}
      <div className="animate-fadeIn">
        {step === 'upload' && <ResumeUpload onSuccess={() => setStep('form')} />}
        {step === 'form' && <CandidateForm onSuccess={() => setStep('jobs')} />}
        {step === 'jobs' && candidateId && <JobList candidateId={candidateId} />}
      </div>
    </div>
  );
};

interface StepIndicatorProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  completed: boolean;
  stepNumber: number;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({
  icon,
  label,
  active,
  completed,
  stepNumber,
}) => (
  <div className="flex flex-col items-center">
    <div
      className={`
        w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-all duration-300
        ${
          active
            ? 'bg-primary-600 text-white shadow-lg scale-110'
            : completed
            ? 'bg-green-500 text-white'
            : 'bg-gray-300 text-gray-600'
        }
      `}
    >
      {completed ? <CheckCircle className="w-6 h-6" /> : icon}
    </div>
    <span
      className={`text-xs md:text-sm font-medium text-center ${
        active ? 'text-primary-700' : 'text-gray-600'
      }`}
    >
      {label}
    </span>
  </div>
);
