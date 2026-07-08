import { Routes, Route, Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import Sidebar from "./components/Sidebar.jsx";
import Landing from "./pages/Landing.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import CheckIn from "./pages/CheckIn.jsx";
import Query from "./pages/Query.jsx";
import Profile from "./pages/Profile.jsx";

function Page({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

function AppLayout() {
  const location = useLocation();
  return (
    <div className="flex h-full min-h-screen bg-ink-900">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 py-7">
          <AnimatePresence mode="wait">
            <div key={location.pathname}>
              <Page>
                <Outlet />
              </Page>
            </div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="checkin" element={<CheckIn />} />
        <Route path="query" element={<Query />} />
        <Route path="profile" element={<Profile />} />
      </Route>
    </Routes>
  );
}
