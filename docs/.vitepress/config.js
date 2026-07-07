import { defineConfig } from 'vitepress'
import { resolve } from 'path'

export default defineConfig({
  title: 'knownleges Wiki',
 head: [
 ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
 ['link', { rel: 'stylesheet', href: '/styles/custom.css' }]
 ],
  base: '/',
  ignoreDeadLinks: true,
  vite: {
    resolve: {
      alias: {
        '/images/': resolve(__dirname, '../public/images/')
      }
    },
    build: {
      rollupOptions: {
        external: [/^\/images\//]
      }
    }
  },
  markdown: {
    image: {
      lazyLoading: true
    }
  },
  themeConfig: {
  logo: '/logo.svg',
  siteTitle: 'knownleges Wiki',
  nav: [
  { text: '首页', link: '/' },
  { text: '标签', link: '/tags' }
  ],
  search: {
  provider: 'local',
  options: {
  detailedView: true
  }
  }
  }
})