export default function ThemeToggle(){
  const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  const toggle = () => {
    const el = document.documentElement
    const darkNow = el.classList.toggle('dark')
    try { localStorage.setItem('theme', darkNow ? 'dark' : 'light') } catch {}
  }
  return (
    <button onClick={toggle} className="px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-sm">
      Toggle {isDark? 'Light':'Dark'}
    </button>
  )
}

