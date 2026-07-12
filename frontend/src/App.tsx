import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ProfilesPage from "./pages/ProfilesPage";
import ProfileEditPage from "./pages/ProfileEditPage";
import ListingListPage from "./pages/ListingListPage";
import ListingDetailPage from "./pages/ListingDetailPage";
import SearchPage from "./pages/SearchPage";
import RecommendPage from "./pages/RecommendPage";
import FavoritesPage from "./pages/FavoritesPage";
import CommunityEvalPage from "./pages/CommunityEvalPage";
import NeedMatchPage from "./pages/NeedMatchPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/listings" element={<ListingListPage />} />
        <Route path="/listings/:id" element={<ListingDetailPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/community-eval" element={<CommunityEvalPage />} />
        <Route path="/ai-match" element={<NeedMatchPage />} />

        <Route path="/profiles" element={<ProtectedRoute><ProfilesPage /></ProtectedRoute>} />
        <Route path="/profiles/new" element={<ProtectedRoute><ProfileEditPage /></ProtectedRoute>} />
        <Route path="/profiles/:id/edit" element={<ProtectedRoute><ProfileEditPage /></ProtectedRoute>} />
        <Route path="/recommend" element={<ProtectedRoute><RecommendPage /></ProtectedRoute>} />
        <Route path="/favorites" element={<ProtectedRoute><FavoritesPage /></ProtectedRoute>} />
      </Routes>
    </Layout>
  );
}
