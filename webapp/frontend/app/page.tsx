export default function HomePage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-2xl mx-auto p-8 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Cleo</h1>
        <p className="text-gray-600 mb-8">Unify Data. Unlock Deals.</p>
        <div className="space-x-4">
          <a href="/dashboard" className="inline-block rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700">Open Dashboard</a>
          <a href="/login" className="inline-block rounded border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-100">Login</a>
        </div>
        <p className="text-xs text-gray-400 mt-6">This is a placeholder landing page for local development.</p>
      </div>
    </main>
  )
}
