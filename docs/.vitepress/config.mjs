import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'A2W: Lucas',
  description: 'Kubernetes-native agent for pod health checks and hotfixes.',
  lang: 'en-US',
  lastUpdated: true,
  themeConfig: {
    logo: {
      light: '/logo-dark.png',
      dark: '/logo-dark.png'
    },
    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'Ops', link: '/ops/deployment' }
    ],
    search: {
      provider: 'local'
    },
    sidebar: {
      '/guide/': [
        {
          text: 'Introduction',
          collapsed: false,
          items: [
            { text: 'Getting Started', link: '/guide/getting-started' },
            { text: 'Architecture', link: '/guide/architecture' }
          ]
        },
        {
          text: 'Functionality',
          collapsed: false,
          items: [
            { text: 'Configuration', link: '/guide/configuration' },
            { text: 'Slack Usage', link: '/guide/slack' }
          ]
        },
        {
          text: 'Deployment',
          collapsed: false,
          items: [
            { text: 'Build Images', link: '/guide/build' }
          ]
        }
      ],
      '/ops/': [
        {
          text: 'Deployment',
          collapsed: false,
          items: [
            { text: 'Overview', link: '/ops/deployment' },
            { text: 'ArgoCD', link: '/ops/deployment-argocd' },
            { text: 'Plain YAML', link: '/ops/deployment-yaml' },
            { text: 'CronJob Mode', link: '/ops/cronjob' }
          ]
        },
        {
          text: 'Operations',
          collapsed: false,
          items: [
            { text: 'Dashboard', link: '/ops/dashboard' },
            { text: 'Operations', link: '/ops/operations' },
            { text: 'Runbooks', link: '/ops/runbooks' },
            { text: 'Troubleshooting', link: '/ops/troubleshooting' }
          ]
        }
      ]
    },
    footer: {
      message: 'Short docs. Clear actions.',
      copyright: 'A2W: Lucas'
    }
  }
})
