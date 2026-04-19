import { Routes, Route, NavLink } from 'react-router-dom'
import { UserProvider } from './context/UserContext'
import MapPage from './pages/MapPage'
import ProfilePage from './pages/ProfilePage'
import { MapPin, User } from 'lucide-react'

export default function App() {
  return (
    <UserProvider>
      <div className="flex flex-col h-screen">
        <nav className="flex items-center justify-between px-4 py-2 bg-white border-b shadow-sm z-50">
          <span className="font-bold text-blue-600 text-lg">Predictive Transit</span>
          <div className="flex gap-4">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `flex items-center gap-1 text-sm font-medium ${isActive ? 'text-blue-600' : 'text-gray-500 hover:text-gray-800'}`
              }
            >
              <MapPin size={16} /> Map
            </NavLink>
            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `flex items-center gap-1 text-sm font-medium ${isActive ? 'text-blue-600' : 'text-gray-500 hover:text-gray-800'}`
              }
            >
              <User size={16} /> Profile
            </NavLink>
          </div>
        </nav>

        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<MapPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Routes>
        </main>
      </div>
    </UserProvider>
  )
}
