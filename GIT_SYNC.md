# 修复：vue-doc-qa-chat 未正确上传到 Git

## 原因说明

**vue-doc-qa-chat** 目录内有自己的 `.git`，Git 会把它当成「内嵌仓库」处理，只记录一条引用，**不会**把里面的文件逐个纳入版本控制，所以 `git status` 会显示 `modified: vue-doc-qa-chat (modified content)`，GitHub 上也看不到前端源码。

## 解决步骤（在仓库根目录执行）

在 **Git Bash** 或 **WSL** 下，进入仓库根目录后按顺序执行：

### 1. 从索引中移除 vue-doc-qa-chat（不再当作子模块/内嵌仓库）

```bash
git rm --cached vue-doc-qa-chat
```

### 2. 删除 vue-doc-qa-chat 内部的 .git

```bash
rm -rf vue-doc-qa-chat/.git
```

### 3. 重新添加为普通目录并提交

```bash
git add vue-doc-qa-chat/
git add README.md GIT_SYNC.md
git status
```

确认 `git status` 里能看到大量 `vue-doc-qa-chat/` 下的文件（如 `vue-doc-qa-chat/src/`、`vue-doc-qa-chat/package.json` 等），而不是只有一项 `vue-doc-qa-chat`。

```bash
git commit -m "fix: 将 vue-doc-qa-chat 作为普通目录纳入仓库"
git push origin main
```

---

## 其他环境下的等价命令

**PowerShell（删除 .git）：**
```powershell
Remove-Item -Recurse -Force vue-doc-qa-chat\.git
```

**CMD（删除 .git）：**
```cmd
rd /s /q vue-doc-qa-chat\.git
```

---

完成后，在 GitHub 上应能看到 `vue-doc-qa-chat/` 下的完整目录和文件。
