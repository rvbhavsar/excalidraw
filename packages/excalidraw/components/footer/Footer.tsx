import clsx from "clsx";

import { actionShortcuts, actionToggleTheme } from "../../actions";
import { useTunnels } from "../../context/tunnels";
import { ExitZenModeButton, UndoRedoActions, ZoomActions } from "../Actions";
import { DarkModeToggle } from "../DarkModeToggle";
import { HelpButton } from "../HelpButton";
import { InputDeviceToggle } from "../InputDeviceToggle";
import { Section } from "../Section";
import Stack from "../Stack";

import type { ActionManager } from "../../actions/manager";
import type { AppState, UIAppState } from "../../types";

const Footer = ({
  appState,
  actionManager,
  showExitZenModeBtn,
  renderWelcomeScreen,
  setAppState,
}: {
  appState: UIAppState;
  actionManager: ActionManager;
  showExitZenModeBtn: boolean;
  renderWelcomeScreen: boolean;
  setAppState: React.Component<any, AppState>["setState"];
}) => {
  const { FooterCenterTunnel, WelcomeScreenHelpHintTunnel } = useTunnels();

  return (
    <footer
      role="contentinfo"
      className="layer-ui__wrapper__footer App-menu App-menu_bottom"
    >
      <div
        className={clsx("layer-ui__wrapper__footer-left zen-mode-transition", {
          "layer-ui__wrapper__footer-left--transition-left":
            appState.zenModeEnabled,
        })}
      >
        <Stack.Row gap={2} align="center">
          <Section heading="canvasActions">
            {!appState.viewModeEnabled && (
              <UndoRedoActions
                renderAction={actionManager.renderAction}
                className={clsx("zen-mode-transition", {
                  "layer-ui__wrapper__footer-left--transition-bottom":
                    appState.zenModeEnabled,
                })}
              />
            )}
          </Section>
          {!appState.viewModeEnabled && !appState.zenModeEnabled && (
            <InputDeviceToggle
              mode={appState.inputDeviceMode}
              onChange={(inputDeviceMode) => setAppState({ inputDeviceMode })}
            />
          )}
        </Stack.Row>
      </div>
      <FooterCenterTunnel.Out />
      <div
        className={clsx("layer-ui__wrapper__footer-right zen-mode-transition", {
          "transition-right": appState.zenModeEnabled,
        })}
      >
        <div style={{ position: "relative", display: "flex", gap: "0.5rem" }}>
          {renderWelcomeScreen && <WelcomeScreenHelpHintTunnel.Out />}
          <ZoomActions
            renderAction={actionManager.renderAction}
            zoom={appState.zoom}
          />
          {actionManager.isActionEnabled(actionToggleTheme) && (
            <DarkModeToggle
              value={appState.theme}
              onChange={() => actionManager.executeAction(actionToggleTheme)}
            />
          )}
          <HelpButton
            onClick={() => actionManager.executeAction(actionShortcuts)}
          />
        </div>
      </div>
      <ExitZenModeButton
        actionManager={actionManager}
        showExitZenModeBtn={showExitZenModeBtn}
      />
    </footer>
  );
};

export default Footer;
Footer.displayName = "Footer";
