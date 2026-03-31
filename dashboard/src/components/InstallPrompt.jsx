import { useState, useEffect } from 'react'
import { Download, X } from 'lucide-react'

export function InstallPrompt() {
  const [prompt, setPrompt] = useState(null)
  const [visible, setVisible] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (dismissed) return
    const handler = (e) => {
      e.preventDefault()
      setPrompt(e)
      setVisible(true)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [dismissed])

  async function install() {
    if (!prompt) return
    prompt.prompt()
    const { outcome } = await prompt.userChoice
    if (outcome === 'accepted') setVisible(false)
  }

  function dismiss() {
    setVisible(false)
    setDismissed(true)
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 animate-fade-in">
      <div className="bg-surface-700 border border-brand-400/30 rounded-2xl p-4 shadow-2xl glow-green-sm flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-400/10 border border-brand-400/20 flex items-center justify-center shrink-0">
          <Download size={18} className="text-brand-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-100">Instalar como app</p>
          <p className="text-xs text-slate-400">Acceso rápido desde tu pantalla de inicio</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={install}
            className="px-3 py-1.5 bg-brand-400/10 border border-brand-400/20 text-brand-400 rounded-lg text-xs font-medium hover:bg-brand-400/20 transition-colors"
          >
            Instalar
          </button>
          <button
            onClick={dismiss}
            className="p-1.5 text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
