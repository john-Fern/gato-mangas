import { HashRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import Logo from './Logo'
import Favorites from './pages/Favorites'
import Home from './pages/Home'
import ImportManga from './pages/ImportManga'
import Login from './pages/Login'
import MangaPage from './pages/MangaPage'
import Reader from './pages/Reader'
import { supabase, useSession } from './supabase'

function Header() {
  const session = useSession()
  const email = session?.user.email ?? ''
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link to="/" className="logo">
          <Logo />
          <span>
            Gato <b>Mangas</b>
          </span>
        </Link>
        <nav>
          <NavLink to="/" end>
            Explorar
          </NavLink>
          {session && <NavLink to="/favorites">Favoritos</NavLink>}
          {session && <NavLink to="/import">Importar</NavLink>}
        </nav>
        <div className="account">
          {session ? (
            <>
              <span className="avatar" title={email}>
                {email.charAt(0).toUpperCase()}
              </span>
              <button className="ghost" onClick={() => supabase?.auth.signOut()}>
                Salir
              </button>
            </>
          ) : (
            <Link to="/login" className="button pill">
              Entrar
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <HashRouter>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/manga/:id" element={<MangaPage />} />
          <Route path="/read/:mangaId/:chapterId" element={<Reader />} />
          <Route path="/favorites" element={<Favorites />} />
          <Route path="/import" element={<ImportManga />} />
          <Route path="/login" element={<Login />} />
        </Routes>
      </main>
      <footer>Datos e imágenes de MangaDex.</footer>
    </HashRouter>
  )
}
