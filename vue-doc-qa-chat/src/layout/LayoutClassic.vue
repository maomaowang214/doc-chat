<script setup lang="ts">
import LayoutHeader from './components/base/LayoutHeader.vue'
import LayoutAside from './components/base/LayoutAside.vue'
import LayoutFooter from './components/base/LayoutFooter.vue'
</script>

<template>
  <el-container class="layout">
    <el-header>
      <LayoutHeader></LayoutHeader>
    </el-header>

    <el-container class="layout-body">
      <el-aside>
        <LayoutAside></LayoutAside>
      </el-aside>

      <el-main>
        <el-scrollbar class="layout-scrollbar">
          <div class="layout-main">
            <router-view v-slot="{ Component }">
              <keep-alive include="Chat">
                <component :is="Component" />
              </keep-alive>
            </router-view>
          </div>
          <!-- <LayoutFooter class="el-footer" /> -->
        </el-scrollbar>
        <el-backtop target=".layout-scrollbar .el-scrollbar__wrap" :right="50" :bottom="60" />
      </el-main>
    </el-container>
  </el-container>
</template>

<style lang="scss" scoped>
.layout {
  position: relative;
  width: 100vw;
  height: 100vh;
  background-color: #343541;

  .el-header {
    padding: 0 10px;
    background-color: #202123;
    border-bottom: 1px solid #444654;
  }

  .layout-body {
    height: 0;

    .el-aside {
      background-color: #202123;
      border-right: 1px solid #444654;
    }

    .el-main {
      padding: 0;
      background-color: #343541;
    }

    .el-footer {
      background-color: #343541;
      border-top: 1px solid #444654;
    }
  }

  .layout-main {
    min-height: calc(100vh - var(--el-header-height) - var(--el-footer-height));
    padding: 20px;
    color: #e5e5e5;
  }
}
</style>
