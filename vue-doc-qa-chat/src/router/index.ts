import { createRouter, createWebHistory } from 'vue-router'
import LayoutClassic from '@/layout/LayoutClassic.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/chat'
    },
    {
      path: '/',
      component: LayoutClassic,
      children: [
        {
          path: '/chat',
          name: 'Chat',
          meta: {
            title: '聊天',
            icon: 'ChatDotRound',
            keepAlive: true
          },
          component: () => import('@/views/chat/index.vue')
        },
        {
          path: '/knowledge',
          name: 'Knowledge',
          meta: {
            title: '知识库管理',
            icon: 'FolderOpened'
          },
          component: () => import('@/views/knowledge/index.vue')
        },
        {
          path: '/model-config',
          name: 'ModelConfig',
          meta: {
            title: '模型管理',
            icon: 'Setting'
          },
          component: () => import('@/views/model-config/index.vue')
        }
      ]
    }
  ]
})

export default router
