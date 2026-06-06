/** @jsxImportSource @opentui/solid */
import type { TuiPlugin, TuiPluginModule } from "@opencode-ai/plugin/tui"

const tui: TuiPlugin = async (api, _options, _meta) => {
  api.slots.register({
    slots: {
      home_prompt(ctx, value) {
        const Prompt = api.ui.Prompt
        const Slot = api.ui.Slot

        return (
          <Prompt
            workspaceID={value.workspace_id}
            ref={value.ref}
            right={<Slot name="home_prompt_right" workspace_id={value.workspace_id} />}
            placeholders={{
              normal: [
                [
                  "/delegate",
                  "@planner implement go-task-orbit into core, replacing existing worker",
                  "@result @coder make changes in branch refactor-worker",
                  "@result @reviewer review the changes against main",
                ].join("\n"),
                [
                  "/delegate",
                  "@coder fix payment timeout bug",
                  "@coder add logging to notification service",
                  "@result @tester verify both changes",
                ].join("\n"),
                [
                  "/delegate",
                  "@planner design auth system migration",
                  "@result @coder implement auth changes",
                  "@coder implement billing changes",
                  "@result @reviewer review both",
                  "@result @tester run integration tests",
                ].join("\n"),
              ],
              shell: ["ls -la", "git status", "pwd"],
            }}
          />
        )
      },
    },
  })
}

const plugin: TuiPluginModule & { id: string } = {
  id: "delegate-placeholders",
  tui,
}
export default plugin
