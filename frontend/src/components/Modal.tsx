export default function Modal({ open, title, children }:{ open:boolean, title?:string, children?:any }){
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md mx-4 p-4 card">
        {title && <h3 className="text-lg font-semibold mb-2">{title}</h3>}
        <div className="text-sm">{children}</div>
      </div>
    </div>
  )
}

