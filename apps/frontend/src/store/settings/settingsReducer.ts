// apps/frontend/src/store/settings/settingsReducer.ts
import { SettingState, SettingAction } from './interface';
import {
  updateTitle,
  updateThemeScheme,
  updateBodyClass,
  updateHtmlAttr,
  updateHtmlClass,
  updateColorRootVar,
  updateStorage,
  updateDomValueBySetting,
} from '@/utilities/setting';
import { setFontFamily } from '@/utilities/root-var';
import { defaultState } from './state';

const Choices = {
  SchemeChoice: defaultState.setting.theme_scheme.choices,
  ColorChoice: defaultState.setting.theme_color.choices,
  StyleAppearanceChoice: defaultState.setting.theme_style_appearance.choices,
  CardStyle: defaultState.setting.card_style.choices,
  FSChoice: defaultState.setting.theme_font_size.choices,
  Animation: defaultState.setting.theme_transition.choices,
};

// Side effects map
const settingSideEffects = {
  app_name: (value: string) => updateTitle(value),
  theme_scheme_direction: (value: string) => updateHtmlAttr({ prop: 'dir', value }),
  theme_scheme: (value: string, state: SettingState) =>
    updateThemeScheme(value, Choices, state.setting.theme_color),
  theme_style_appearance: (value: string[]) =>
    updateBodyClass(Choices.StyleAppearanceChoice, value),
  theme_transition: (value: string) => updateBodyClass(Choices.Animation, value),
  theme_font_size: (value: string) => updateHtmlClass(Choices.FSChoice, value),
  card_style: (value: string) => updateBodyClass(Choices.CardStyle, value),
  body_font_family: (value: string) => setFontFamily('body', value),
  heading_font_family: (value: string) => setFontFamily('heading', value),
};

export function settingsReducer(state: SettingState, action: SettingAction): SettingState {
  switch (action.type) {
    case 'RESET': {
      const setting = JSON.parse(JSON.stringify(defaultState.setting));
      updateDomValueBySetting(setting, Choices);
      if (state.saveLocal !== 'none') {
        updateStorage(state.saveLocal, state.storeKey, { ...state, setting });
      }
      return { ...state, setting };
    }

    case 'SET_SAVE_LOCATION': {
      const newState = { ...state, saveLocal: action.payload };
      if (action.payload !== 'none') {
        updateStorage(action.payload, state.storeKey, newState);
      }
      return newState;
    }

    case 'UPDATE_SETTING': {
      const { key, value } = action.payload;
      const setting = {
        ...state.setting,
        [key]: { ...state.setting[key], value },
      };
      const newState = { ...state, setting };

      const effect = (settingSideEffects as any)[key];
      if (effect) effect(value, newState);

      if (newState.saveLocal !== 'none') {
        updateStorage(newState.saveLocal, newState.storeKey, newState);
      }

      return newState;
    }

    case 'UPDATE_THEME_COLOR': {
      const { colors, value } = action.payload;
      const setting = {
        ...state.setting,
        theme_color: {
          ...state.setting.theme_color,
          colors: { ...state.setting.theme_color.colors, ...colors },
          value,
        },
      };
      updateColorRootVar(
        state.setting.theme_scheme.value,
        setting.theme_color,
        Choices.ColorChoice
      );

      const newState = { ...state, setting };
      if (state.saveLocal !== 'none') {
        updateStorage(state.saveLocal, state.storeKey, newState);
      }
      return newState;
    }

    default:
      return state;
  }
}
