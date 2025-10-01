import Link from 'next/link'

export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full text-center">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">403</h1>
          <h2 className="text-2xl font-semibold text-gray-700 mb-4">Access Denied</h2>
          <p className="text-gray-600 mb-8">
            You don't have permission to access this resource. Please contact your administrator if you believe this is an error.
          </p>
        </div>

        <div className="space-y-4">
          <Link
            href="/dashboard"
            className="inline-block bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 transition-colors"
          >
            Go to Dashboard
          </Link>
          <div>
            <Link
              href="/login"
              className="text-indigo-600 hover:text-indigo-800"
            >
              Sign in with different account
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}