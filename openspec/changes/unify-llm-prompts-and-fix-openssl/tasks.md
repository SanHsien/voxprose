## 1. Centralize system prompts in llm/prompts.py

- [x] 1.1 Create `llm/prompts.py` with SYSTEM_PROMPTS dict containing zh, en, ja language variants
- [x] 1.2 Implement `get_default_system_prompt(language: str = "zh")` function
- [x] 1.3 Add docstring explaining prompt fallback behavior and language selection
- [x] 1.4 Verify prompts match existing defaults in OpenRouter, MiniMax, and other LLM classes

## 2. Fix LLM classes to use default when prompt is empty

- [x] 2.1 Modify `llm/openrouter.py` refine() method to use `prompt or get_default_system_prompt(self.language)`
- [x] 2.2 Modify `llm/minimax.py` refine() method to use default fallback
- [x] 2.3 Modify `llm/claude.py` refine() method to use default fallback
- [x] 2.4 Modify `llm/gemini.py` refine() method to use default fallback
- [x] 2.5 Modify `llm/qwen.py` refine() method to use default fallback
- [x] 2.6 Modify `llm/deepseek.py` refine() method to use default fallback
- [x] 2.7 Modify `llm/ollama.py` refine() method to use default fallback
- [x] 2.8 Modify `llm/openai_llm.py` refine() method to use default fallback
- [x] 2.9 Update `llm/__init__.py` to import and export `get_default_system_prompt`

## 3. Implement install_name_tool rpath fix

- [x] 3.1 Add `fix_libssl_rpath()` function to `post_build_fix.py` that calls `install_name_tool -change` to rewrite libcrypto.3.dylib path to @loader_path
- [x] 3.2 Add comprehensive logging to document which dylibs are patched and their new rpath values
- [x] 3.3 Add error handling to catch install_name_tool failures and report them clearly

## 4. Integrate rpath fix into build_all.sh

- [x] 4.1 Call `fix_libssl_rpath()` in `build_all.sh` immediately after py2app completes (before DMG signing)
- [x] 4.2 Add logging output to show when rpath fix is being applied
- [x] 4.3 Ensure build script fails loudly if rpath fix fails

## 5. Testing and validation

- [ ] 5.1 Verify on development machine that refine() calls with empty prompt use defaults
- [ ] 5.2 Build complete DMG on development machine
- [ ] 5.3 Verify on brand-new Mac Mini that application launches without manual OpenSSL installation
- [ ] 5.4 Verify LLM refine() produces meaningful output (not hallucinations) when user config has empty llm_prompt
- [ ] 5.5 Check that otool -L output shows @loader_path for libcrypto.3.dylib
- [ ] 5.6 Verify backward compatibility: existing refine() calls with explicit prompts still work

## 6. Cleanup and documentation

- [x] 6.1 Remove any hardcoded system prompts from individual LLM class constructors
- [x] 6.2 Update CLAUDE.md or code comments documenting the centralized prompt system
- [x] 6.3 Create or update developer notes about language fallback behavior
