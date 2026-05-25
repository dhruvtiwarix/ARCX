import { create } from 'zustand'

export const useThemeStore = create((set) => ({
  theme: localStorage.getItem('arcx-theme') || 'dark', // Default to dark for our aesthetic
  
  setTheme: (newTheme) => {
    set({ theme: newTheme })
    localStorage.setItem('arcx-theme', newTheme)
    
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else if (newTheme === 'light') {
      document.documentElement.classList.remove('dark')
    } else {
      // system
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }
  },

  initTheme: () => {
    const theme = localStorage.getItem('arcx-theme') || 'dark'
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else if (theme === 'light') {
      document.documentElement.classList.remove('dark')
    } else {
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }
    set({ theme })
  }
}))
