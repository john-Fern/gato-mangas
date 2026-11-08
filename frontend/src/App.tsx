import { HashRouter, Link, Route, Routes } from 'react-router-dom'
import Favorites from './pages/Favorites'
import Home from './pages/Home'
import Login from './pages/Login'
import MangaPage from './pages/MangaPage'
import Reader from './pages/Reader'
import { supabase, useSession } from './supabase'

export default function App() {
  const session = useSession()
  return (
    <HashRouter>
      <header className="topbar">
        <Link to="/" className="logo">
          🐱 Gato Mangas
        </Link>
        <nav>
          {session ? (
            <>
              <Link to="/favorites">Favoritos</Link>
              <button className="link" onClick={() => supabase?.auth.signOut()}>
                Salir
              </button>
            </>
          ) : (
            <Link to="/login">Entrar</Link>
          )}
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/manga/:id" element={<MangaPage />} />
          <Route path="/read/:mangaId/:chapterId" element={<Reader />} />
          <Route path="/favorites" element={<Favorites />} />
          <Route path="/login" element={<Login />} />
        </Routes>
      </main>
      <footer>Datos e imágenes de MangaDex.</footer>
    </HashRouter>
  )
}
