import React from 'react';
import { NavLink, useParams } from 'react-router-dom';
import {
  FolderGit2,
  LayoutDashboard,
  MessageSquareCode,
  GraduationCap,
  Sparkles,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { id: repoId } = useParams<{ id: string }>();

  return (
    <aside className="w-64 border-r border-dark-800 bg-dark-900 flex flex-col h-screen sticky top-0">
      {/* Brand Logo */}
      <div className="h-16 flex items-center px-6 gap-3 border-b border-dark-800">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-brand-500/30">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <span className="font-bold text-lg text-white tracking-tight">CodeSage</span>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 px-4 py-6 space-y-6 overflow-y-auto">
        <div>
          <div className="text-xs font-semibold uppercase text-slate-500 px-3 mb-2 tracking-wider">
            Workspace
          </div>
          <div className="space-y-1">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white hover:bg-dark-800'
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </NavLink>
            <NavLink
              to="/repos"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white hover:bg-dark-800'
                }`
              }
            >
              <FolderGit2 className="w-4 h-4" />
              Repositories
            </NavLink>
          </div>
        </div>

        {/* Repository Context Modules */}
        {repoId && (
          <div>
            <div className="text-xs font-semibold uppercase text-slate-500 px-3 mb-2 tracking-wider">
              Repo Intelligence
            </div>
            <div className="space-y-1">
              <NavLink
                to={`/repos/${repoId}`}
                end
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30' : 'text-slate-400 hover:text-white hover:bg-dark-800'
                  }`
                }
              >
                <FolderGit2 className="w-4 h-4" />
                Files Explorer
              </NavLink>

              <NavLink
                to={`/repos/${repoId}/chat`}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30' : 'text-slate-400 hover:text-white hover:bg-dark-800'
                  }`
                }
              >
                <MessageSquareCode className="w-4 h-4" />
                RAG Assistant
              </NavLink>

              <NavLink
                to={`/repos/${repoId}/interview`}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30' : 'text-slate-400 hover:text-white hover:bg-dark-800'
                  }`
                }
              >
                <GraduationCap className="w-4 h-4" />
                Interview Engine
              </NavLink>
            </div>
          </div>
        )}
      </nav>
    </aside>
  );
};
