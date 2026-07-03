import { GOOGLE_FONTS_RANGES } from "@excalidraw/common";

import { type ExcalidrawFontFaceDescriptor } from "../Fonts";

import DMMonoLatinExt from "./DMMono-Medium-LatinExt.woff2";
import DMMonoLatin from "./DMMono-Medium-Latin.woff2";

export const DMMonoFontFaces: ExcalidrawFontFaceDescriptor[] = [
  {
    uri: DMMonoLatinExt,
    descriptors: { unicodeRange: GOOGLE_FONTS_RANGES.LATIN_EXT },
  },
  {
    uri: DMMonoLatin,
    descriptors: { unicodeRange: GOOGLE_FONTS_RANGES.LATIN },
  },
];
