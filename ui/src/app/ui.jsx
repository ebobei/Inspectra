import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import en from '../locales/en'
import ru from '../locales/ru'

const dictionaries = { en, ru }

const UIContext = createContext(null)

function getByPath(obj, path) {
  return path.split('.').reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : undefined), obj)
}

export function UIProvider({ children }) {
  const [locale, setLocale] = useState(() => localStorage.getItem('inspectra_locale') || 'en')
  const [theme, setTheme] = useState(() => localStorage.getItem('inspectra_theme') || 'dark')

  useEffect(() => {
    localStorage.setItem('inspectra_locale', locale)
  }, [locale])

  useEffect(() => {
    localStorage.setItem('inspectra_theme', theme)
    document.documentElement.classList.remove('theme-light', 'theme-dark')
    document.documentElement.classList.add(`theme-${theme}`)
    document.documentElement.style.colorScheme = theme
  }, [theme])

  const value = useMemo(() => ({
    locale,
    setLocale,
    theme,
    setTheme,
    t: (key) => getByPath(dictionaries[locale] || dictionaries.en, key) ?? key,
  }), [locale, theme])

  return <UIContext.Provider value={value}>{children}</UIContext.Provider>
}

export function useUI() {
  const value = useContext(UIContext)
  if (!value) {
    throw new Error('useUI must be used within UIProvider')
  }
  return value
}
