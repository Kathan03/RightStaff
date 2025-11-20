import React from 'react';
import { RankedCandidate } from '../../types';
import { TrendingUp, Award, Users, Target } from 'lucide-react';

interface CandidateRankingProps {
  candidates: RankedCandidate[];
  onSelectCandidate?: (candidate: RankedCandidate) => void;
}

export const CandidateRanking: React.FC<CandidateRankingProps> = ({
  candidates,
  onSelectCandidate,
}) => {
  // Helper to format score as percentage (clamped to 0-100)
  const formatScore = (score: number | undefined): string => {
    if (score === undefined) return 'N/A';
    const percentage = Math.max(0, Math.min(100, score * 100));
    return `${percentage.toFixed(0)}%`;
  };
  const getBandColor = (band: string) => {
    switch (band.toLowerCase()) {
      case 'high':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  const getBandIcon = (band: string) => {
    switch (band.toLowerCase()) {
      case 'high':
        return <Award className="w-4 h-4" />;
      case 'medium':
        return <TrendingUp className="w-4 h-4" />;
      default:
        return <Users className="w-4 h-4" />;
    }
  };

  if (candidates.length === 0) {
    return (
      <div className="card text-center py-12">
        <Users className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-900 mb-2">No Candidates Yet</h3>
        <p className="text-gray-600">
          Candidates will appear here once they apply to your job posting.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-gray-900">Ranked Candidates</h3>
        <span className="text-sm text-gray-500">{candidates.length} candidates</span>
      </div>

      {candidates.map((candidate, index) => (
        <div
          key={candidate.candidate_id}
          className={`
            card hover:shadow-lg transition-shadow cursor-pointer border-l-4
            ${
              candidate.band.toLowerCase() === 'high'
                ? 'border-green-500'
                : candidate.band.toLowerCase() === 'medium'
                ? 'border-yellow-500'
                : 'border-gray-400'
            }
          `}
          onClick={() => onSelectCandidate?.(candidate)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              {/* Rank and Name */}
              <div className="flex items-center gap-3 mb-3">
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary-100 text-primary-700 font-bold text-lg">
                  #{index + 1}
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-gray-900">
                    Candidate {candidate.candidate_id.slice(0, 8)}
                  </h4>
                  <div
                    className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getBandColor(
                      candidate.band
                    )}`}
                  >
                    {getBandIcon(candidate.band)}
                    {candidate.band.toUpperCase()} MATCH
                  </div>
                </div>
              </div>

              {/* Summary */}
              <p className="text-gray-700 mb-3 text-sm leading-relaxed">{candidate.summary}</p>

              {/* Reasons */}
              {candidate.reasons && candidate.reasons.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-medium text-gray-600 mb-1">Key Strengths:</p>
                  <ul className="space-y-1">
                    {candidate.reasons.slice(0, 3).map((reason, idx) => (
                      <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                        <span className="text-primary-600 mt-1">•</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Evidence Snippets */}
              {candidate.evidence_snippets && candidate.evidence_snippets.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium text-gray-600 mb-1">Evidence:</p>
                  <div className="space-y-1">
                    {candidate.evidence_snippets.slice(0, 2).map((snippet, idx) => (
                      <div key={idx} className="text-xs bg-gray-50 p-2 rounded border border-gray-200">
                        <p className="text-gray-700 italic">"{snippet.text}"</p>
                        <p className="text-gray-500 mt-1">Source: {snippet.source}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Score Section */}
            <div className="ml-6 text-right">
              <div className="flex items-center gap-2 mb-3">
                <Target className="w-6 h-6 text-primary-600" />
                <span className="text-3xl font-bold text-primary-600">
                  {formatScore(candidate.confidence)}
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-3">Confidence Score</p>

              <div className="text-xs text-gray-600 space-y-1 bg-gray-50 p-3 rounded-lg">
                <p className="font-semibold text-gray-700 mb-2">Score Breakdown</p>
                {candidate.score_breakdown.dense_score !== undefined && (
                  <div className="flex justify-between gap-4">
                    <span>Semantic:</span>
                    <span className="font-medium">
                      {formatScore(candidate.score_breakdown.dense_score)}
                    </span>
                  </div>
                )}
                {candidate.score_breakdown.structured_score !== undefined && (
                  <div className="flex justify-between gap-4">
                    <span>Structured:</span>
                    <span className="font-medium">
                      {formatScore(candidate.score_breakdown.structured_score)}
                    </span>
                  </div>
                )}
                {candidate.score_breakdown.pairwise_score !== undefined && (
                  <div className="flex justify-between gap-4">
                    <span>Comparison:</span>
                    <span className="font-medium">
                      {formatScore(candidate.score_breakdown.pairwise_score)}
                    </span>
                  </div>
                )}
                {candidate.score_breakdown.completeness_score !== undefined && (
                  <div className="flex justify-between gap-4">
                    <span>Complete:</span>
                    <span className="font-medium">
                      {formatScore(candidate.score_breakdown.completeness_score)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
