// apps/frontend/src/store/settings/interface.ts
export interface ObjectMap {
  [key: string]: string;
}

export interface SettingValueMap {
  value: string; // Removed null and empty string
}

export interface SettingArrValueMap {
  value: string[];
}

export interface DefaultMap {
  target: string | Element;
  choices: string[];
  type: string;
}

export interface DefaultVStringMap extends DefaultMap, SettingValueMap {}
export interface DefaultVArrayMap extends DefaultMap, SettingArrValueMap {}

export interface SettingState {
  saveLocal: 'localStorage' | 'sessionStorage' | 'none';
  storeKey: string;
  setting: {
    app_name: SettingValueMap;
    theme_scheme: SettingValueMap;
    theme_scheme_direction: SettingValueMap;
    theme_style_appearance: SettingArrValueMap;
    theme_color: {
      colors: ObjectMap;
      value: string;
    };
    theme_transition: SettingValueMap;
    theme_font_size: SettingValueMap;
    page_layout: SettingValueMap;
    header_navbar: SettingValueMap;
    card_style: SettingValueMap;
    header_banner: SettingValueMap;
    sidebar_color: SettingValueMap;
    sidebar_type: SettingArrValueMap;
    sidebar_show: SettingArrValueMap;
    navbar_show: SettingArrValueMap;
    sidebar_menu_style: SettingValueMap;
    footer: SettingValueMap;
    body_font_family: SettingValueMap;
    heading_font_family: SettingValueMap;
  };
}

export interface SettingDefaultState {
  saveLocal: 'localStorage' | 'sessionStorage' | 'none';
  storeKey: string;
  setting: {
    app_name: DefaultVStringMap;
    theme_scheme: DefaultVStringMap;
    theme_scheme_direction: DefaultVStringMap;
    theme_style_appearance: DefaultVArrayMap;
    theme_color: {
      target: string | Element;
      choices: string[];
      type: string;
      colors: ObjectMap;
      value: string;
    };
    theme_transition: DefaultVStringMap;
    theme_font_size: DefaultVStringMap;
    page_layout: DefaultVStringMap;
    header_navbar: DefaultVStringMap;
    card_style: DefaultVStringMap;
    header_banner: DefaultVStringMap;
    sidebar_color: DefaultVStringMap;
    sidebar_type: DefaultVArrayMap;
    sidebar_show: DefaultVArrayMap;
    navbar_show: DefaultVArrayMap;
    sidebar_menu_style: DefaultVStringMap;
    footer: DefaultVStringMap;
    body_font_family: DefaultVStringMap;
    heading_font_family: DefaultVStringMap;
  };
}

export type SettingAction =
  | {
      type: 'RESET';
    }
  | {
      type: 'SET_SAVE_LOCATION';
      payload: 'localStorage' | 'sessionStorage' | 'none';
    }
  | {
      type: 'UPDATE_SETTING';
      payload: {
        key: keyof SettingState['setting'];
        value: string | string[];
      };
    }
  | {
      type: 'UPDATE_THEME_COLOR';
      payload: {
        colors: { [key: string]: string };
        value: string;
      };
    };
