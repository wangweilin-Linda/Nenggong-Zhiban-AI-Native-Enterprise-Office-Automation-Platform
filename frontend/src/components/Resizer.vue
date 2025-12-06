<template>
  <div class="resizer" @mousedown="startResize"></div>
</template>

<script>
export default {
  methods: {
    startResize(e) {
      const workspace = this.$parent.$refs.workspace;
      const aiAssistant = this.$parent.$refs.aiAssistant;
      let isResizing = true;
      let lastX = e.clientX;

      const onMouseMove = (e) => {
        if (!isResizing) return;
        const delta = e.clientX - lastX;
        lastX = e.clientX;

        const newWorkspaceWidth = workspace.workspaceWidth + delta;
        const newAiWidth = aiAssistant.aiWidth - delta;

        if (newWorkspaceWidth >= 400 && newAiWidth >= 300) {
          workspace.workspaceWidth = newWorkspaceWidth;
          aiAssistant.aiWidth = newAiWidth;
        }
      };

      const onMouseUp = () => {
        isResizing = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    }
  }
};
</script>