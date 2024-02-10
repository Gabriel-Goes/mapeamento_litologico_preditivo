require'nvim-treesitter.configs'.setup {
    ensure_installed = {"markdown","python", "c", "lua", "vim", "help"},
    sync_install = true,
    auto_install = true,
    highlight = {
        -- 'false' will disable the whole extension
      enable = true,
      additional_vim_regex_highlighting = true,
    },
}
