import os
import wx

class SharesFrame(wx.Frame):

    def onClose(self, evt):
        self.Hide()

    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, -1, title, size = (400, 320),
            style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE|wx.NO_BORDER)
        self.rebuild()
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def rebuild(self):
        self.share_panels = {}
        self.scrolling_window = wx.ScrolledWindow( self )

        self.Bind(wx.EVT_SIZE, self.OnSize)


        self.scrolling_window.SetScrollRate(8,8)
        self.scrolling_window.EnableScrolling(True,True)
        self.scrolling_window_sizer = wx.BoxSizer( wx.VERTICAL )
        self.scroll_panel_sizer = wx.BoxSizer( wx.VERTICAL )
        self.scrolling_window_sizer.Add(self.scroll_panel_sizer,1,wx.CENTER,wx.EXPAND)
        self.scrolling_window.SetSizer(self.scrolling_window_sizer)


        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(self.scrolling_window)

        self.scrolling_window.SetFocus()
        self.Bind(wx.EVT_SET_FOCUS, self.onFocus)

        self.scrolling_window.Layout()
        self.SetSizer(frame_sizer)
        self.Layout()

    def OnSize(self, event):
        self.scrolling_window.SetSize(self.GetClientSize())

    def onFocus(self, event):
        self.scrolling_window.SetFocus()

    def add_share(self, share, callbacks={}):
        filename = share.filePath

        share_panel = wx.Panel(self.scrolling_window, id=share.id)
        self.scroll_panel_sizer.Add(share_panel, 0, wx.ALL|wx.EXPAND,0)
        share_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        top_panel = wx.Panel(share_panel)
        top_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        filename_text = wx.StaticText(top_panel, -1, os.path.basename(filename))
        filename_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        filename_text.SetSize(filename_text.GetBestSize())
        top_panel_sizer.Add(filename_text, 0, wx.ALL, 10)

        def stop_sharing(evt):
            if 'stop' in callbacks:
                callbacks['stop'](share)
        stop_sharing_button = wx.Button(top_panel, -1, label="Stop sharing")
        stop_sharing_button.Bind(wx.EVT_BUTTON, stop_sharing)
        top_panel_sizer.Add(stop_sharing_button, 0, wx.ALL, 10)


        top_panel.SetSizer(top_panel_sizer)
        share_panel_sizer.Add(top_panel, 0, wx.ALL, 10)

        dir_text = wx.StaticText(share_panel, -1, os.path.dirname(filename))
        dir_text.SetSize(dir_text.GetBestSize())
        share_panel_sizer.Add(dir_text, 0, wx.ALL, 10)

        share_panel.SetSizer(share_panel_sizer)
        share_panel.Layout()
        self.share_panels[share.id] = share_panel
        self.scrolling_window.Layout()

    def remove_share(self, share):
        self.scrolling_window.RemoveChild(self.share_panels[share.id])
        self.scrolling_window_sizer.Remove(self.share_panels[share.id])
        self.share_panels[share.id].Destroy()
        self.share_panels.pop(share.id)

def main():
    from dbhandler import DBHandler

    app = wx.App(False)
    frame = SharesFrame(None, -1, ' ')
    dbhandler = DBHandler()

    shares = dbhandler.get_shares()
    for share in shares:
        frame.add_share(share)

#    frame.Show(False)
    frame.Show(True)
    app.MainLoop()

    pass

if __name__ == '__main__':
    main()