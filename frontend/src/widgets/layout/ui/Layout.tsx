import type {FC, PropsWithChildren, ReactNode} from "react"

export interface LayoutProps extends PropsWithChildren {
  header: ReactNode;
}

export const Layout: FC<LayoutProps> = ({header, children}: LayoutProps) => {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="bg-blue-700 text-white px-6 py-4 shadow">
        {header}
      </header>
      <main id="main-content" tabIndex={-1} className="max-w-5xl mx-auto p-6">
        {children}
      </main>
    </div>
  )
};
