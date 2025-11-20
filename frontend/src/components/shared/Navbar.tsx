import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Briefcase, Users } from 'lucide-react';

export const Navbar: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <Briefcase className="w-8 h-8 text-primary-600" />
            <span className="text-xl font-bold text-gray-900">RightStaff</span>
          </Link>

          {/* Navigation Links */}
          <div className="flex space-x-4">
            <Link
              to="/"
              className={`
                flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors
                ${
                  isActive('/')
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-50'
                }
              `}
            >
              <Users className="w-5 h-5" />
              <span>Candidate Portal</span>
            </Link>
            <Link
              to="/recruiter"
              className={`
                flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors
                ${
                  isActive('/recruiter')
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-50'
                }
              `}
            >
              <Briefcase className="w-5 h-5" />
              <span>Recruiter Dashboard</span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};
