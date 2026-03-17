import { Suspense, lazy } from "react";
import { createBrowserRouter, Navigate, Outlet, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { useAppStore } from "./store/useAppStore";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { OnboardingPage } from "./pages/OnboardingPage";

const MapPage = lazy(() => import("./pages/MapPage").then((m) => ({ default: m.MapPage })));
const ChatPage = lazy(() => import("./pages/ChatPage").then((m) => ({ default: m.ChatPage })));

function Layout() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-4">
        <Outlet />
      </main>
    </div>
  );
}

function Protected() {
  const user = useAppStore((s) => s.user);
  const isDemo = useAppStore((s) => s.isDemo);
  const setDemo = useAppStore((s) => s.setDemo);
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const demoParam = params.get("demo");
  const hasDemoParam = demoParam === "delhi" || demoParam === "bangalore" || demoParam === "mumbai";

  useEffect(() => {
    if (hasDemoParam) {
      setDemo(demoParam as "delhi" | "bangalore" | "mumbai");
    }
  }, [hasDemoParam, demoParam, setDemo]);

  if (!user && !isDemo && !hasDemoParam) {
    return <Navigate to="/login" replace />;
  }
  return <Layout />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/onboarding", element: <OnboardingPage /> },
  {
    element: <Protected />,
    children: [
      { path: "/", element: <DashboardPage /> },
      {
        path: "/map",
        element: (
          <Suspense fallback={<div className="animate-pulse rounded bg-slate-200 p-10">Loading map...</div>}>
            <MapPage />
          </Suspense>
        )
      },
      {
        path: "/chat",
        element: (
          <Suspense fallback={<div className="animate-pulse rounded bg-slate-200 p-10">Loading chat...</div>}>
            <ChatPage />
          </Suspense>
        )
      }
    ]
  }
]);
