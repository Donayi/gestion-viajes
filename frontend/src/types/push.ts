export type BrowserPushPermission = NotificationPermission | "unsupported";

export type PushSubscriptionPayload = {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  user_agent?: string | null;
};

export type PushStatusResponse = {
  enabled: boolean;
  vapid_public_key_configured: boolean;
  has_active_subscriptions: boolean;
  active_subscriptions_count: number;
};

export type PushTestResponse = {
  enviado: boolean;
  mensaje: string;
};
