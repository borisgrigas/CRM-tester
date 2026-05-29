import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "./components/ui/sonner";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Contacts from "./pages/Contacts";
import ContactDetail from "./pages/ContactDetail";
import Pipeline from "./pages/Pipeline";
import Tasks from "./pages/Tasks";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import AdminCompanies from "./pages/AdminCompanies";
import AdminUsers from "./pages/AdminUsers";
import AdminPanel from "./features/admin/AdminPanel";
import MapPage from "./features/map/MapPage";
import FranchisePage from "./features/franchise/FranchisePage";
import WhatsAppPage from "./features/whatsapp/WhatsAppPage";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import ModuleGuard from "./components/ModuleGuard";
import { useAuthStore } from "./stores/authStore";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 30_000 },
  },
});

function Bootstrap({ children }) {
  const refreshMe = useAuthStore((s) => s.refreshMe);
  useEffect(() => {
    refreshMe();
  }, [refreshMe]);
  return children;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Bootstrap>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Dashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Dashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/contacts"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Contacts />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/contacts/:id"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ContactDetail />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/pipeline"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Pipeline />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/tasks"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Tasks />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Analytics />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Settings />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/whatsapp"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ModuleGuard module="whatsapp" level="view">
                      <WhatsAppPage />
                    </ModuleGuard>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/franchise"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ModuleGuard module="franchise" level="view">
                      <FranchisePage />
                    </ModuleGuard>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/map"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ModuleGuard module="map">
                      <MapPage />
                    </ModuleGuard>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ModuleGuard module="admin" level="manage">
                      <AdminPanel />
                    </ModuleGuard>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ModuleGuard module="admin" level="manage">
                      <AdminUsers />
                    </ModuleGuard>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/companies"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ModuleGuard module="admin" level="manage">
                      <AdminCompanies />
                    </ModuleGuard>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Bootstrap>
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
