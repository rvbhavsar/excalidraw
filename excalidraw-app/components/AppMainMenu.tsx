import {
  loginIcon,
  eyeIcon,
  PlusIcon,
  TrashIcon,
} from "@excalidraw/excalidraw/components/icons";
import { MainMenu } from "@excalidraw/excalidraw/index";
import React from "react";

import { isDevEnv } from "@excalidraw/common";
import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/clerk-react";

import type { Theme } from "@excalidraw/element/types";

import { useAtomValue } from "../app-jotai";
import {
  createDrawing,
  currentDrawingIdAtom,
  deleteDrawing,
} from "../data/backend";
import { LanguageList } from "../app-language/LanguageList";

import { saveDebugState } from "./DebugCanvas";

const CLERK_ENABLED = !!import.meta.env.VITE_APP_CLERK_PUBLISHABLE_KEY;

const handleNewDrawing = async () => {
  try {
    const drawing = await createDrawing();
    window.location.assign(`/d/${drawing.id}`);
  } catch (error) {
    console.error("failed to create drawing", error);
  }
};

const handleDeleteDrawing = async (drawingId: string) => {
  // eslint-disable-next-line no-alert
  if (!window.confirm("Delete this drawing? This can't be undone.")) {
    return;
  }
  try {
    await deleteDrawing(drawingId);
    window.location.assign("/dashboard");
  } catch (error) {
    console.error("failed to delete drawing", error);
  }
};

export const AppMainMenu: React.FC<{
  onCollabDialogOpen: () => any;
  isCollaborating: boolean;
  isCollabEnabled: boolean;
  theme: Theme | "system";
  refresh: () => void;
}> = React.memo((props) => {
  const currentDrawingId = useAtomValue(currentDrawingIdAtom);
  return (
    <MainMenu>
      <MainMenu.DefaultItems.LoadScene />
      <MainMenu.DefaultItems.SaveToActiveFile />
      <MainMenu.DefaultItems.Export />
      <MainMenu.DefaultItems.SaveAsImage />
      {props.isCollabEnabled && (
        <MainMenu.DefaultItems.LiveCollaborationTrigger
          isCollaborating={props.isCollaborating}
          onSelect={() => props.onCollabDialogOpen()}
        />
      )}
      <MainMenu.DefaultItems.CommandPalette className="highlighted" />
      <MainMenu.DefaultItems.SearchMenu />
      <MainMenu.DefaultItems.Help />
      <MainMenu.DefaultItems.ClearCanvas />
      <MainMenu.Separator />
      {CLERK_ENABLED && (
        <>
          <SignedIn>
            <MainMenu.Item
              icon={loginIcon}
              onSelect={() => window.location.assign("/dashboard")}
            >
              Dashboard
            </MainMenu.Item>
            <MainMenu.Item icon={PlusIcon} onSelect={handleNewDrawing}>
              New drawing
            </MainMenu.Item>
            {currentDrawingId && (
              <MainMenu.Item
                icon={TrashIcon}
                onSelect={() => handleDeleteDrawing(currentDrawingId)}
              >
                Delete drawing
              </MainMenu.Item>
            )}
            <MainMenu.ItemCustom>
              <UserButton afterSignOutUrl={window.location.origin} />
            </MainMenu.ItemCustom>
          </SignedIn>
          <SignedOut>
            <MainMenu.ItemCustom>
              <SignInButton mode="modal">
                <button className="aix-sign-in-button">Sign in</button>
              </SignInButton>
            </MainMenu.ItemCustom>
          </SignedOut>
        </>
      )}
      {isDevEnv() && (
        <MainMenu.Item
          icon={eyeIcon}
          onSelect={() => {
            if (window.visualDebug) {
              delete window.visualDebug;
              saveDebugState({ enabled: false });
            } else {
              window.visualDebug = { data: [] };
              saveDebugState({ enabled: true });
            }
            props?.refresh();
          }}
        >
          Visual Debug
        </MainMenu.Item>
      )}
      <MainMenu.Separator />
      <MainMenu.DefaultItems.Preferences />
      <MainMenu.DefaultItems.ToggleTheme allowSystemTheme theme={props.theme} />
      <MainMenu.ItemCustom>
        <LanguageList style={{ width: "100%" }} />
      </MainMenu.ItemCustom>
      <MainMenu.DefaultItems.ChangeCanvasBackground />
    </MainMenu>
  );
});
