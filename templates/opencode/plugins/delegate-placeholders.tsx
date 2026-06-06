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
                  "@plan implement go-task-orbit into core, replacing existing worker",
                  "@result @code make changes in branch refactor-worker",
                  "@result @review review the changes against aus-testing",
                ].join("\n"),
                [
                  "/delegate",
                  "@code fix payment timeout bug",
                  "@code add logging to notification service",
                  "@result @test verify both changes",
                ].join("\n"),
                [
                  "/delegate",
                  "@plan design auth system migration",
                  "@result @code implement auth changes",
                  "@code implement billing changes",
                  "@result @review review both",
                  "@result @test run integration tests",
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
