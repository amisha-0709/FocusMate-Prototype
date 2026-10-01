import { Clerk } from "@clerk/clerk-js";
import { publishableKeyFromHost } from "@clerk/shared/keys";

const config = window.__FOCUSMATE_CLERK_CONFIG__;

if (config) {
  window.__fmClerkReady = (async () => {
    if (!config.publishableKey) {
      throw new Error("FocusMate sign-in is not configured.");
    }

    const publishableKey = publishableKeyFromHost(
      window.location.hostname,
      config.publishableKey,
    );
    if (!publishableKey) {
      throw new Error("FocusMate could not resolve its sign-in configuration.");
    }

    const clerkDomain = atob(publishableKey.split("_")[2]).slice(0, -1);
    const proxyUrl = config.proxyUrl || "";
    const routerNavigate = (to, metadata, replace = false) => {
      const destination = new URL(to, window.location.origin);
      if (destination.origin !== window.location.origin) {
        if (metadata?.windowNavigate) metadata.windowNavigate(destination);
        else window.location.assign(destination.href);
        return;
      }
      const url = `${destination.pathname}${destination.search}${destination.hash}`;
      if (replace) window.history.replaceState({}, "", url);
      else window.history.pushState({}, "", url);
      window.dispatchEvent(new PopStateEvent("popstate"));
    };

    const clerk = new Clerk(publishableKey, {
      proxyUrl,
      routerPush: (to, metadata) => routerNavigate(to, metadata),
      routerReplace: (to, metadata) => routerNavigate(to, metadata, true),
    });

    const uiBase = proxyUrl
      ? proxyUrl.replace(/\/$/, "")
      : `https://${clerkDomain}`;
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = `${uiBase}/npm/@clerk/ui@1/dist/ui.browser.js`;
      script.async = true;
      script.crossOrigin = "anonymous";
      script.onload = resolve;
      script.onerror = () => reject(new Error("Could not load the sign-in interface."));
      document.head.appendChild(script);
    });

    const appearanceForTheme = () => {
      const light = document.documentElement.getAttribute("data-fm-theme") === "light";
      const palette = light
        ? {
            primary: "#9A5B0A",
            foreground: "#211F24",
            muted: "#686570",
            background: "#FFFCF6",
            input: "#FFFFFF",
            inputForeground: "#211F24",
            neutral: "#817E89",
            border: "#E7E1D7",
          }
        : {
            primary: "#FFB547",
            foreground: "#F4F1EA",
            muted: "#A8A5B2",
            background: "#17171D",
            input: "#202128",
            inputForeground: "#F4F1EA",
            neutral: "#797785",
            border: "#393843",
          };
      return {
        options: {
          logoPlacement: "inside",
          logoLinkUrl: "/",
          logoImageUrl: `${window.location.origin}/focusmate-mark.svg`,
          socialButtonsPlacement: "top",
          socialButtonsVariant: "blockButton",
        },
        variables: {
          colorPrimary: palette.primary,
          colorForeground: palette.foreground,
          colorMutedForeground: palette.muted,
          colorDanger: "#C34F43",
          colorBackground: palette.background,
          colorInput: palette.input,
          colorInputForeground: palette.inputForeground,
          colorNeutral: palette.neutral,
          fontFamily: "'Manrope', sans-serif",
          borderRadius: "16px",
        },
        elements: {
          rootBox: { width: "100%", display: "flex", justifyContent: "center" },
          cardBox: {
            width: "100%",
            maxWidth: "360px",
            backgroundColor: palette.background,
            border: `1px solid ${palette.border}`,
            borderRadius: "22px",
            overflow: "hidden",
          },
          card: { backgroundColor: "transparent", border: "none", boxShadow: "none" },
          footer: { backgroundColor: "transparent", border: "none", boxShadow: "none" },
          headerTitle: { color: palette.foreground, fontWeight: "800" },
          headerSubtitle: { color: palette.muted },
          socialButtonsBlockButtonText: { color: palette.foreground, fontWeight: "700" },
          formFieldLabel: { color: palette.foreground, fontWeight: "700" },
          formFieldInput: {
            color: palette.inputForeground,
            backgroundColor: palette.input,
            borderColor: palette.border,
          },
          formButtonPrimary: { color: light ? "#FFFFFF" : "#24170A", fontWeight: "800" },
          footerActionLink: { color: palette.primary, fontWeight: "700" },
          footerActionText: { color: palette.muted },
          dividerText: { color: palette.muted },
          alertText: { color: palette.foreground },
        },
      };
    };

    const localization = {
      signIn: {
        start: {
          title: "Welcome back",
          subtitle: "Sign in to continue your study journey.",
        },
      },
      signUp: {
        start: {
          title: "Create your FocusMate account",
          subtitle: "Set up your account and start studying.",
        },
      },
    };

    await clerk.load({
      ui: { ClerkUI: window.__internal_ClerkUICtor },
      localization,
    });

    const identity = (user) => {
      if (!user) return null;
      const email =
        user.primaryEmailAddress?.emailAddress ||
        user.emailAddresses?.[0]?.emailAddress ||
        "";
      return {
        id: user.id,
        email,
        name: user.firstName || user.username || email.split("@")[0] || "",
      };
    };

    window.__fmClerk = clerk;
    let mountedNode = null;
    let mountedMode = null;
    const mountWidget = (node, mode) => {
      if (!node) return;
      mountedNode = node;
      mountedMode = mode;
      const componentProps = {
        routing: "path",
        appearance: appearanceForTheme(),
      };
      if (mode === "login") {
        clerk.mountSignIn(node, { ...componentProps, path: "/sign-in", signUpUrl: "/sign-up" });
      } else {
        clerk.mountSignUp(node, { ...componentProps, path: "/sign-up", signInUrl: "/sign-in" });
      }
    };
    window.__fmMountAuthWidget = mountWidget;
    window.__fmUnmountAuthWidget = (node) => {
      if (!node) return;
      try {
        clerk.unmountSignIn(node);
      } catch {}
      try {
        clerk.unmountSignUp(node);
      } catch {}
      if (mountedNode === node) {
        mountedNode = null;
        mountedMode = null;
      }
    };
    window.addEventListener("fm-theme", () => {
      if (mountedNode?.isConnected) {
        const node = mountedNode;
        const mode = mountedMode;
        window.__fmUnmountAuthWidget(node);
        mountWidget(node, mode);
      }
    });

    let previousUserId = clerk.user?.id || null;
    clerk.addListener(({ user }) => {
      const nextUserId = user?.id || null;
      if (nextUserId !== previousUserId) {
        previousUserId = nextUserId;
        window.location.assign("/");
      }
    });

    return { clerk, user: identity(clerk.user) };
  })();
}