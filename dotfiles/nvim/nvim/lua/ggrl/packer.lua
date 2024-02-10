print("Sourcing Packages")
vim.cmd [[]]
vim.cmd [[packadd packer.nvim]]

return require('packer').startup(function(use)
    require'nvim-treesitter.configs'.setup {
      ensure_installed = "all",  -- Certifique-se de instalar todas as linguagens
      highlight = {
        enable = true,  -- Ativar realce de sintaxe
      },
    }

    use 'python-mode/python-mode'
    use 'wbthomason/packer.nvim'
    use {'nvim-telescope/telescope.nvim', tag = '0.1.5',
            -- or                       , branch = '0.1.x',
            requires = { {'nvim-lua/plenary.nvim'} }
        }
    use({'rose-pine/neovim',
            as = 'rose-pine',
            config = function()
                vim.cmd('colorscheme rose-pine')
            end
        })
    use('mbbill/undotree')
    use('tpope/vim-fugitive')
    use('nvim-treesitter/nvim-treesitter', {run = ':TSUpdate'})
    use('nvim-treesitter/playground')
    use('theprimeagen/harpoon')
    use 'nvim-lua/popup.nvim'
    use 'nvim-lua/plenary.nvim'
    use 'junegunn/fzf'
    use 'junegunn/fzf.vim'
    use 'BurntSushi/ripgrep'
    use { 'nvim-telescope/telescope-fzf-native.nvim', run = 'cmake -S. -Bbuild -DCMAKE_BUILD_TYPE=Release && cmake --build build --config Release && cmake --install build --prefix build' }
    -- CMD Autocompletion
    use 'neovim/nvim-lspconfig'
    use 'hrsh7th/cmp-nvim-lsp'
    use 'hrsh7th/cmp-buffer'
    use 'hrsh7th/cmp-path'
    use 'hrsh7th/cmp-cmdline'
    use 'hrsh7th/nvim-cmp'
    use 'saadparwaiz1/cmp_luasnip'
    use 'L3MON4D3/LuaSnip'

     -- Neotest
    use ('nvim-neotest/neotest')
    use ('nvim-neotest/neotest-python')
    use 'sharkdp/fd'
    use {'VonHeikemen/lsp-zero.nvim',
        requires = {
            -- LSP Support
            {'neovim/nvim-lspconfig'},
            {'williamboman/mason.nvim'},
            {'williamboman/mason-lspconfig.nvim'},

            -- Autocompletion
            {'hrsh7th/nvim-cmp'},
            {'hrsh7th/cmp-buffer'},
            {'hrsh7th/cmp-path'},
            {'saadparwaiz1/cmp_luasnip'},
            {'hrsh7th/cmp-nvim-lsp'},
            {'hrsh7th/cmp-nvim-lua'},

            -- Snippets
            {'L3MON4D3/LuaSnip'},
            {'rafamadriz/friendly-snippets'},
            }
        }
    use 'vim-airline/vim-airline'
    use 'vim-airline/vim-airline-themes'
    use 'edkolev/tmuxline.vim'

    -- Colors
    use 'folke/tokyonight.nvim'
    use 'morhetz/gruvbox'

    -- UML plugin
    use 'javiorfo/nvim-soil'
    use 'javiorfo/nvim-nyctophilia'
    use 'aklt/plantuml-syntax'

    -- Open in browser
    use 'tyru/open-browser.vim'
end)

