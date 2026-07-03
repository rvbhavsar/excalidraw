import { GOOGLE_FONTS_RANGES } from "@excalidraw/common";

import { type ExcalidrawFontFaceDescriptor } from "../Fonts";

import QuicksandLatinExt from "./Quicksand-Medium-LatinExt.woff2";
import QuicksandLatin from "./Quicksand-Medium-Latin.woff2";

export const QuicksandFontFaces: ExcalidrawFontFaceDescriptor[] = [
  {
    uri: QuicksandLatinExt,
    descriptors: { unicodeRange: GOOGLE_FONTS_RANGES.LATIN_EXT },
  },
  {
    uri: QuicksandLatin,
    descriptors: { unicodeRange: GOOGLE_FONTS_RANGES.LATIN },
  },
];
