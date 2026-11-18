import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { MainLayout } from './components/layout/MainLayout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { ReposListPage } from './pages/ReposListPage';
import { RepoDetailPage } from './pages/RepoDetailPage';
import { ChatPage } from './pages/ChatPage';
import { InterviewPage } from './pages/InterviewPage';
import { LoadingSpinner } from './components/common/LoadingSpinner';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, token, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-dark-950 flex items-center justify-center">
        <LoadingSpinner text="Authenticating..." />
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  const { loadUser } = useAuthStore();

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="repos" element={<ReposListPage />} />
        <Route path="repos/:id" element={<RepoDetailPage />} />
        <Route path="repos/:id/chat" element={<ChatPage />} />
        <Route path="repos/:id/interview" element={<InterviewPage />} />
        <Route path="repos/:id/review" element={<Navigate to="../" relative="path" replace />} />
        <Route path="repos/:id/docs" element={<Navigate to="../" relative="path" replace />} />
        <Route path="repos/:id/analytics" element={<Navigate to="../" relative="path" replace />} />
        <Route path="repos/:id/graph" element={<Navigate to="../" relative="path" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
